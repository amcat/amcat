##########################################################################
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
import datetime
import pickle
import zlib
import re

import dateutil.parser
import functools
import hashlib

import settings
from amcat.models import Project, ArticleSet, TaskHandler, CodingJob
from amcat.models.authorisation import ROLE_PROJECT_METAREADER
from amcat.scripts.forms import SelectionForm
from amcat.tools.caching import cached
from amcat.tools.progress import ProgressMonitor
from django import forms
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.cache import cache
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.urlresolvers import reverse
from django.http import QueryDict, HttpResponse
from navigator.views.scriptview import CeleryProgressUpdater
from settings import SECRET_KEY

DOWNLOAD_HEADER = "Content-Disposition: attachment; "
RE_CAPITALS = re.compile("([A-Z])")

def to_querydict(dict):
    """
    Converts a value created by querydict_dict back into a Django QueryDict value.
    """
    q = QueryDict("", mutable=True)
    for k, v in dict.items():
        q.setlist(k, v)
    q._mutable = False
    return q


class QueryActionForm(SelectionForm):
    output_type = forms.ChoiceField(choices=())
    download = forms.BooleanField(initial=False, required=False)

    def __init__(self, user, *args, **kwargs):
        super(QueryActionForm, self).__init__(*args, **kwargs)
        self.user = user


class QueryActionHandler(TaskHandler):
    @classmethod
    def serialise_arguments(cls, arguments):
        arguments = super(QueryActionHandler, cls).serialise_arguments(arguments)
        user = arguments['user']
        arguments['user'] = None if user.is_anonymous() else user.id
        arguments['project'] = arguments['project'].id
        arguments['articlesets'] = [aset.id for aset in arguments['articlesets']]
        arguments['codingjobs'] = [cj.id for cj in arguments.get('codingjobs', [])]

        if arguments['data'] is not None and isinstance(arguments["data"], QueryDict):
            arguments['data'] = dict(arguments['data'].lists())

        return arguments

    @classmethod
    def deserialise_arguments(cls, arguments):
        arguments = super(QueryActionHandler, cls).deserialise_arguments(arguments)
        arguments['user'] = None if arguments['user'] is None else User.objects.get(id=arguments['user'])
        arguments['project'] = Project.objects.get(id=arguments['project'])
        arguments['articlesets'] = ArticleSet.objects.filter(id__in=arguments['articlesets'])
        arguments['codingjobs'] = CodingJob.objects.filter(id__in=arguments.get('codingjobs', []))

        if arguments['data'] is not None:
            arguments['data'] = to_querydict(arguments['data'])

        return arguments

    @cached
    def get_query_action(self):
        query_action = self.task.get_class()(**self.task.get_arguments())
        query_action.get_form().full_clean()
        return query_action

    def run_task(self):
        query_action = self.get_query_action()
        updater = CeleryProgressUpdater(str(self.task.uuid))
        query_action.monitor.add_listener(updater.update)

        msg = "Task started, running {query_action.__class__.__name__}..".format(**locals())
        query_action.monitor.update(0, msg)

        try:
            form = query_action.get_form()
            query_action.before_run(form)
            result = query_action.run(form)
            cache_key = query_action.get_cache_key() if query_action.cache_hit else None
            return cache_key, result
        except Exception as e:
            raise

    def _get_content_type(self):
        """Returns content type of selected 'output_type'. This usually is a mimetype
        formatted like:

            application/json
            text/csv

        If clients want to add a specific 'meaning' to the data, the can add it using
        the separator comma:

            application/json,normalise
            text/csv,sparse

        In the latter cases only the part before the comma will be send back to the client
        as Content-Type header.
        """
        form = self.get_query_action().get_form()
        content_type = form.cleaned_data["output_type"]
        content_type = content_type.split(";")[0]
        return content_type

    def get_response(self):
        cache_key, result = self.get_result()
        response = HttpResponse(content=result)
        response["X-Query-Cache-Hit"] = int(cache_key is not None)
        if cache_key:
            response["X-Query-Cache-Key"] = cache_key
            timestamp = cache.get("{}.timestamp".format(cache_key))
            timestamp = dateutil.parser.parse(timestamp)
            response["X-Query-Cache-Timestamp"] = timestamp.isoformat()
            response["X-Query-Cache-Natural-Timestamp"] = naturaltime(timestamp)
        response["Content-Disposition"] = "attachment"
        response["Content-Type"] = self._get_content_type()
        return response

    def get_redirect(self):
        return reverse("api:queryaction-index"), "No redirect"


class NotInCacheError(Exception):
    pass


def is_valid_cache_key(cache_key):
    return len(cache_key) == 64 + 12 and cache_key.endswith(".query-cache")


class QueryAction(object):
    form_class = QueryActionForm
    task_handler = QueryActionHandler
    output_types = None
    required_role = ROLE_PROJECT_METAREADER
    ignore_cache_fields = ("output_type",)
    monitor_steps = None

    def __init__(self, user, project, articlesets, codingjobs=None, data=None, api_host=None):
        """
        @type project: amcat.models.Project
        @type articlesets: django.db.QuerySet
        @type data: NoneType, django.http.QueryDict
        """
        self.user = user
        self.project = project
        self.api_host = api_host
        self.articlesets = articlesets
        self.codingjobs = codingjobs
        self.data = data
        self.cache_hit = False

        if self.monitor_steps is None:
            self.monitor = ProgressMonitor()
        else:
            self.monitor = ProgressMonitor(total=self.monitor_steps)

        assert(issubclass(self.form_class, SelectionForm))

    @functools.lru_cache()
    def get_cache_key(self) -> str:
        """Returns a cache key (SHA256 hexdigest) of user id and form hash. To prevent guessing
        attacks, we also embed the Django SECRET_KEY (240 random bits in AmCAT)."""
        form_hash = self.get_form().get_hash(ignore_fields=self.ignore_cache_fields)
        query_hash = hashlib.sha256("{}|{}|{}".format(SECRET_KEY, self.user.id, form_hash).encode("ascii")).hexdigest()
        return "{}.query-cache".format(query_hash)

    def serialize_cache_value(self, value):
        """Pickle then compress value"""
        return zlib.compress(pickle.dumps(value))

    def desearialize_cache_value(self, value):
        """Decompress then depickle value"""
        try:
            return pickle.loads(zlib.decompress(value))
        except AttributeError:
            raise NotInCacheError("Failed to deserialize cache value")

    def get_cache(self):
        """Get cached value for this particular form+user. Raises NotInCacheError if not cached
        value is found."""
        cache_key = self.get_cache_key()
        value = cache.get(cache_key)
        if value is None:
            raise NotInCacheError("Cache value for {} was not found".format(cache_key))
        self.cache_hit = True
        return self.desearialize_cache_value(value)

    def set_cache(self, value):
        """Sets cache for this particular form+user to 'value'. The value is serialized
        with QueryAction.serialize_cache_value. Note that large values may not fit in
        memcached."""
        timestamp = datetime.datetime.now().isoformat()
        key = self.get_cache_key()
        timeout = settings.CACHE_QUERYACTION_TIMEOUT
        cache.set("{}.timestamp".format(key), timestamp, timeout=timeout+1)
        cache.set(key, self.serialize_cache_value(value), timeout=timeout)

    def get_form_kwargs(self, **kwargs):
        return dict({
            "data": self.data, "project": self.project,
            "articlesets": self.articlesets, "user": self.user,
            "codingjobs": self.codingjobs
        }, **kwargs)

    def get_form_class(self):
        return self.form_class

    def get_task_handler(self):
        return self.task_handler

    def target_project(self, form):
        return self.project
        
    @cached
    def get_form(self) -> SelectionForm:
        form = self.form_class(**self.get_form_kwargs())
        form.fields["output_type"].choices = self.output_types

        if len(self.output_types) <= 1:
            form.fields["output_type"].widget.attrs["type"] = "hidden"

        return form

    def before_run(self, form):
        self.check_permission(form)
        
    def run(self, form):
        """Needs to be overriden by subclass. Return value must be at least
        json serialisable, preferably bytes.

        @param form: cleaned form
        @type form: (subclass of) QueryActionForm"""
        raise NotImplementedError

    def run_delayed(self):
        """
        Put this task in celery queue. Returns a task handler.

        @raises: django.core.exceptions.ValidationError if form invalid
        @rtype: QueryActionHandler
        """
        form = self.get_form()

        if not form.is_valid():
            raise ValidationError(form._errors)
        self.check_permission(form)
            
        return self.get_task_handler().call(
            target_class=self.__class__, user=self.user,
            project=self.project, arguments={
                "user": self.user, "project": self.project, "api_host": self.api_host,
                "data": self.data, "articlesets": self.articlesets,
                "codingjobs": self.codingjobs
            }
        )

    def check_permission(self, form):
        project = self.target_project(form)
        actual = project.get_role_id(self.user)
        if actual < self.required_role:
            raise PermissionDenied("User has no permission to perform {self.__class__.__name__}"
                                   " on project {project}".format(**locals()))

    @classmethod
    def get_action_name(cls):
        if hasattr(cls, "action_name"):
            return cls.action_name
        name = cls.__name__
        if name.endswith("Action"):
            name = name[:-6]
        return name.lower()

    @classmethod
    def get_action_label(cls):
        if hasattr(cls, "action_label"):
            return cls.action_label
        name = cls.__name__
        if name.endswith("Action"):
            name = name[:-6]
        return RE_CAPITALS.sub(" \\1", name).strip()
