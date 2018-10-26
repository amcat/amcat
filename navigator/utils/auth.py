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
import logging
import threading

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

import amcat.tools.toolkit
import settings.tools
from amcat.models.user import create_user as _create_user
from amcat.tools import sendmail

log=logging.getLogger(__name__)

def get_request():
    th = threading.current_thread()
    return th.request if hasattr(th, 'request') else None

def create_user(username, first_name, last_name, email,  password=None):
    """
    This function creates an user with the given properties. Moreover: it
    generates a passwords and emails it to the new user.

    Raises: smtplib.SMTPException, django.db.utils.DatabaseError
    """
    email_password = (password is None)
    if password is None:
        password = amcat.tools.toolkit.random_alphanum(7)
        
    log.info("Creating new user: {username}".format(**locals()))

    u = _create_user(username, first_name, last_name, email, password=password)

    log.info("Created new user, sending email...")
    html = render(get_request(), "welcome_email.html", locals()).content.decode()
    text = render(get_request(), "welcome_email.txt", locals()).content.decode()
    sender = settings.EMAIL_DEFAULT_FROM
    n = sendmail.sendmail(sender, email, 'Welcome to AmCAT!',
                      html, text)
    log.info("{} emails sent, done!".format(n))
    return u


class RequireLoginMiddleware(MiddlewareMixin):
    """
    This middleware forces a login_required decorator for all views
    """
    def __init__(self, get_response):
        super().__init__(get_response)
        self.no_login = (
            settings.ACCOUNTS_URL,
            settings.MEDIA_URL,
            settings.STATIC_URL,
            settings.API_URL
            )

    def _login_required(self, url):
        """
        Check if login is required for this url. Excluded are the login- and
        logout url, plus all (static) media.
        """
        return (settings.REQUIRE_LOGON) and not any([url.startswith(u) for u in self.no_login])

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated and self._login_required(request.path):
            return login_required(view_func)(request, *view_args, **view_kwargs)

class NginxRequestMethodFixMiddleware(MiddlewareMixin):
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

class SetRequestContextMiddleware(MiddlewareMixin):
    """
    This middleware installs `request` in the local thread storage
    """
    def process_request(self, request):
        threading.current_thread().request = request

class HTTPAccessControl(MiddlewareMixin):
    def process_response(self, request, response):
        if settings.DEBUG:
            response["Access-Control-Allow-Origin"] = ",".join(settings.ACCESS_CONTROL_ORIGINS)
            response["Access-Control-Allow-Methods"] = ",".join(settings.ACCESS_CONTROL_METHODS)
            response["Access-Control-Allow-Headers"] = ",".join(settings.ACCESS_CONTROL_HEADERS)
        return response
