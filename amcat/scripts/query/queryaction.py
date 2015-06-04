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
import traceback
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import QueryDict, HttpResponse
import sys
from amcat.models import Project, ArticleSet, TaskHandler
from amcat.scripts.forms import SelectionForm
from django import forms
from amcat.tools.caching import cached
from amcat.tools.progress import ProgressMonitor
from navigator.views.scriptview import CeleryProgressUpdater

DOWNLOAD_HEADER = "Content-Disposition: attachment; "


def to_querydict(dict):
    """
    Converts a value created by querydict_dict back into a Django QueryDict value.
    """
    q = QueryDict("", mutable=True)
    for k, v in dict.iteritems():
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
        arguments['user'] = arguments['user'].id
        arguments['project'] = arguments['project'].id
        arguments['articlesets'] = [aset.id for aset in arguments['articlesets']]

        if arguments['data'] is not None and not isinstance(arguments["data"], dict):
            arguments['data'] = dict(arguments['data'].lists())

        return arguments

    @classmethod
    def deserialise_arguments(cls, arguments):
        arguments = super(QueryActionHandler, cls).deserialise_arguments(arguments)
        arguments['user'] = User.objects.get(id=arguments['user'])
        arguments['project'] = Project.objects.get(id=arguments['project'])
        arguments['articlesets'] = ArticleSet.objects.filter(id__in=arguments['articlesets'])

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
            return query_action.run(query_action.get_form())
        except Exception as e:
            traceback.print_exc(e, sys.stderr)
            sys.stderr.flush()
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
        response = HttpResponse(content=self.get_result())
        response["Content-Disposition"] = "attachment"
        response["Content-Type"] = self._get_content_type()
        return response

    def get_redirect(self):
        return reverse("api:queryaction-index"), "No redirect"


class QueryAction(object):
    """
    A QueryAction
    """
    form_class = QueryActionForm
    task_handler = QueryActionHandler
    output_types = None

    def __init__(self, user, project, articlesets, data=None):
        """
        @type project: amcat.models.Project
        @type articlesets: django.db.QuerySet
        @type data: NoneType, django.http.QueryDict
        """
        self.user = user
        self.project = project
        self.articlesets = articlesets
        self.data = data
        self.monitor = ProgressMonitor()

        assert(issubclass(self.form_class, SelectionForm))

    def get_form_kwargs(self, **kwargs):
        return dict({
            "data": self.data, "project": self.project,
            "articlesets": self.articlesets, "user": self.user
        }, **kwargs)

    def get_form_class(self):
        return self.form_class

    def get_task_handler(self):
        return self.task_handler

    @cached
    def get_form(self):
        form = self.form_class(**self.get_form_kwargs())
        form.fields["output_type"].choices = self.output_types

        if len(self.output_types) <= 1:
            form.fields["output_type"].widget.attrs["type"] = "hidden"

        return form

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

        return self.get_task_handler().call(
            target_class=self.__class__, user=self.user,
            project=self.project, arguments={
                "user": self.user, "project": self.project,
                "data": self.data, "articlesets": self.articlesets
            }
        )
