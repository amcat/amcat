###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################
"""
This module contains the authentication handling.
"""
from base64 import b64decode
from django.conf import settings
from django.contrib.auth import authenticate, login

from django.core.exceptions import PermissionDenied
from django.http import Http404
 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from functools import wraps

from django.http import HttpResponse
from django.shortcuts import render

from amcat.models.user import create_user as _create_user
from amcat.models.user import UserProfile
from amcat.models.project import Project

from amcat.tools import toolkit
from amcat.tools import sendmail

import inspect
import threading

import logging; log=logging.getLogger(__name__)

def get_request():
    th = threading.current_thread()
    return th.request if hasattr(th, 'request') else None

def create_user(username, first_name, last_name, email, affiliation, language, role):
    """
    This function creates an user with the given properties. Moreover: it
    generates a passwords and emails it to the new user.
    """
    password = toolkit.random_alphanum(7)
    log.info("Creating new user: {username}".format(**locals()))
    
    u = _create_user(
        username, first_name, last_name, email,
        affiliation, language, role, password=password
    )
    
    log.info("Created new user, sending email...")
    html = render(get_request(), "utils/welcome_email.html", locals()).content
    text = render(get_request(), "utils/welcome_email.txt", locals()).content
    sendmail.sendmail(settings.DEFAULT_FROM_EMAIL, email, 'Welcome to AmCAT!',
                      html, text)
    log.info("Email sent, done!")
    return u

class check_perm(object):
    """
    This view-decorator checks privilleges against the currently logged
    in user. Example:

        @check_perm("add_articles", onproject=True, arg='pid')
        def articles_upload(request, pid):
            ..
            return HttpResponse("")
    """
    def __init__(self, priv, onproject=False, arg='id'):
        """
        @type priv: string or Privilege object
        @param priv: privllege to check permissions for

        @type onproject: boolean
        @param onproject: check this permission for a project. If this
        option is set, also provide the keyword argument which receives
        the pk-id for the project you want to check against.

        @type arg: basestring
        @param arg: keyword argument which receives the project id for
        the project to check against (if onproject==True).
        """
        assert(isinstance(arg, basestring))

        self.priv = priv
        self.onproject = onproject
        self.arg = arg

    def __call__(self, func):
        @wraps(func)
        def check(request, *args, **kwargs):
            project = None

            if self.onproject:
                try:
                    project = Project.objects.get(id=kwargs[self.arg])
                except Project.DoesNotExist:
                    return HttpResponse("Project not found", status=404)

            # Implementation of haspriv allows project=None
            if not request.user.get_profile().haspriv(self.priv, project):
                raise PermissionDenied()

            return func(request, *args, **kwargs)

        return check


class check(object):
    """
    This view-decorator preforms a few basic checks. It checks if
      * cls.objects.get(**{id=id})        .. it exists
      * model.can_`action`(request.user)  .. the user has correct permissions

    If not it:
      * Returns an 404
      * Returns an 550

    If correct, it executes the view. The arguments of the function will be
    replaced with an argument containing the requested object. For example,
    a view for displaying a user might be defined as:

        def view_user(request, id):
            return response()

    The check funtion replaces `id` with an model object. Thus:

        @check(User)
        def view_user(request, user):
            isinstance(user, model.user.User) # True
            return response()

    If multiple arguments are given by the router, check() replaces them by
    one non-keyword argument. For example:

        def view_prs(request, project, user, role):
            return response()

    becomes:

        @check(ProjectRole, args=['project', 'user', 'role'])
        def view_prs(request, project_role):
            isinstance(project_role, model.auth.ProjectRole) # True
            return response()

    The object will always be passed as the second non-keyword argument, or
    if no second non-keyword argument is specified, the first keyword-argument.

    A router may be configured to give an argument which' key is not available
    on the specified model, but does represent one. With args_map, one may
    map between arguments passed by the url-router and the ones on a model. For
    example:

        def view_codingjob(request, project_id, codingjob_id):
            pass

    becomes:

        @check(Project, args_map=(('project_id', 'id'),))
        def view_codingjob(request, project, codingjob_id):
            pass

    or:

        @check(Project, args_map={'project_id' : 'id'})
        def view_codingjob(request, project, codingjob_id):
            pass

    Of course multiple decorations work just fine. Keep in mind you stack them
    in the right order. Example:

        def view_codingjob(request, project_id, codingjob_id):
            pass

    becomes:

        @check(Project, args_map={'project_id' : 'id'}, args='project')
        @check(CodingJob, args_map={'codingjob_id' : 'id'}, args='codingjob')
        def view_codingjob(request, project, codingjob):
            pass

    """
    def __init__(self, cls, action='read', args='id', args_map=None):
        """
        @type cls: subclass of django.models.Model
        @param cls: class to instanciate / check permissions for

        @type action: basestring
        @param action: check for specific action.

        @type args: basestring, iterable
        @param args: arguments to pass to cls.objects.get.
                     If this is None, check will not instanciate cls.

        @type args_map: dict, tuple with 2-length tuples
        @param args_map: map of arg --> model-property (see docs above)
        """
        self.cls = cls
        self.action = action
        self.args = toolkit.totuple(args)
        self.args_map = dict() if not args_map else dict(args_map)

    def _allows_none(self, func):
        """
        Methods checks if no values may be passed.
        """
        insp = inspect.getargspec(func)
        first_kw = len(insp.args) - (len(insp.defaults) if insp.defaults else 0)

        # No non-keyword argument besides 'request', which indicates a
        # default value for object
        return first_kw == 1


    def __call__(self, func):
        @wraps(func)
        def check(request, *args, **kwargs):
            obj = self.cls

            if self.args:
                if self._allows_none(func) and all([kwargs.get(a, None) is None
                                                    for a in self.args]):
                    # This function allows its object to not be specified and there are no
                    # identifiers given to this 'wrap'-function.
                    for a in self.args:
                        if a in kwargs: # Arguments may not be given
                            del kwargs[a]

                    return func(request, None, *args, **kwargs)

                try:
                    gargs = dict([(self.args_map.get(a, a), kwargs[a]) for a in self.args])
                    obj = self.cls.objects.get(**gargs)
                except self.cls.DoesNotExist:
                    return HttpResponse('%s not found using gargs=%r' % (self.cls.__name__, gargs),
                                        status=404)

            # Since django.contrib.auth.models.User does not inherit from our base-model
            # class, no can_* methods exist. UserProfile does, however.
            if isinstance(obj, User):
                # Get a users profile
                _obj = obj.get_profile()
            elif inspect.isclass(obj) and issubclass(User, obj):
                # Not an instance, but a class (probably checking on can_create)
                _obj = UserProfile
            else:
                # "Normal" class/object
                _obj = obj

            # Check against privillege system
            can = getattr(_obj, 'can_%s' % self.action)
            if not can(request.user):
                raise PermissionDenied("User {request.user} is not allows to '{self.action}' object {_obj!r}".format(**locals()))

            # Delete all id-keywords
            for a in self.args: del kwargs[a]

            if self.args:
                return func(request, obj, *args, **kwargs)
            else:
                return func(request, *args, **kwargs)


        # Return wrap-function
        return check

class RequireLoginMiddleware(object):
    """
    This middleware forces a login_required decorator for all views
    """
    def __init__(self):
        self.no_login = (
            settings.ACCOUNTS_URL,
            settings.MEDIA_URL,
            settings.STATIC_URL
        )

    def _login_required(self, url):
        """
        Check if login is required for this url. Excluded are the login- and
        logout url, plus all (static) media.
        """
        return not any([url.startswith(u) for u in self.no_login])

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated() and self._login_required(request.path):
            return login_required(view_func)(request, *view_args, **view_kwargs)

class BasicAuthenticationMiddleware(object):
    """
    This middleware tries to login a user if the Authorization-header is set. If it
    is not, it continues silently.
    """
    header = "HTTP_AUTHORIZATION"

    def _parse_header(self, header):
        """
        Parse basic auth header

        @return: (user, password)
        """
        return b64decode(header.split()[1]).split(':', 1)

    def _unauthorized(self):
        res = HttpResponse("401 Unauthorized", status=401)
        res['WWW-Authenticate'] = 'Basic realm="%s"' % settings.APPNAME_VERBOSE
        return res

    def process_request(self, request):
        assert hasattr(request, 'session'), "The Django authentication middleware\
                requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES\
                setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."

        b64 = request.META.get(self.header, None)

        # Check if header is in use
        if b64 is None:
            return

        user, passwd = self._parse_header(b64)
        user = authenticate(username=user, password=passwd)

        if user:
            login(request, user)
            return

        return self._unauthorized()

class NginxRequestMethodFixMiddleware(object):
    """
    nginx ignores the content written to the output buffer when:

    1) request.method == "POST"
    2) ~5000 > len(reponse) > 0
    3) request.POST is not read

    By reading request.POST by default, point 3 is eleminated and
    ngix will always return content.
    """
    def process_request(self, request):
        request.POST

class SetRequestContextMiddleware(object):
    """
    This middleware installs `request` in the local thread storage
    """
    def process_request(self, request):
        threading.current_thread().request = request
