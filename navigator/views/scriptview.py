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
import tempfile, os
import base64
from urllib.parse import urlencode

from django.core.files.uploadedfile import SimpleUploadedFile

from django.utils.datastructures import MultiValueDict
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.views.generic.edit import FormMixin, ProcessFormView
from django.views.generic.base import TemplateResponseMixin
from django.http import HttpResponse
from django import forms
from django.db import models
from django.http import QueryDict

from amcat.tools.table import table3
from amcat.tools.progress import ProgressMonitor
from amcat.models.task import TaskHandler, IN_PROGRESS
from amcat.amcatcelery import app

class CeleryProgressUpdater(object):
    def __init__(self, task_id):
        self.task_id = task_id
    def update(self, monitor):
        app.backend.store_result(
            self.task_id,
            {"completed": monitor.percent, "message": monitor.message},
            IN_PROGRESS
        )

class ScriptHandler(TaskHandler):
    def get_form_kwargs(self):
        """
        Get the kwargs to pass to the form for this script. By default, returns the task
        arguments.

        - 'data' list entries converted into a querydict.
        - 'files' list entries converted to File objects
        """
        from logging import getLogger
        log = getLogger(__name__)
        kwargs = self.task.arguments.copy() # don't modify self.task.arguments['data']
        if 'data' in kwargs:
            d = QueryDict('').copy()
            for k, v in kwargs['data'].items():
                if isinstance(v, list):
                    d.setlist(k, v)
                else:
                    d[k] = v
            kwargs['data'] = d

        # Convert file dictionaries (as supplied by get_temporary_file_dict) to
        # SimpleUploadedFile objects which Django understands.
        if 'files' in kwargs:
            files = MultiValueDict()
            files.update(kwargs['files'])
            for key, filedict_list in files.lists():
                for i, fdict in enumerate(filedict_list):
                    if isinstance(fdict, dict):
                        fdict = dict(fdict)
                        fdict["content"] = open(fdict["path"], "rb").read()
                        filedict_list[i] = SimpleUploadedFile.from_dict(fdict)
                        log.warn(fdict)
                files.setlist(key, filedict_list)
            kwargs['files'] = files
        return kwargs

    def get_script(self):
        script_cls = self.task.get_class()
        kwargs = self.get_form_kwargs()
        form = script_cls.options_form(**kwargs)
        return script_cls(form)

    def run_task(self):
        script = self.get_script()
        script.progress_monitor = ProgressMonitor()
        script.progress_monitor.add_listener(CeleryProgressUpdater(str(self.task.uuid)).update)
        script.task = self.task
        result = script.run()
        if isinstance(result, models.Model):
            result = result.pk
        return result

    def get_redirect(self):
        """Default: provide redirect to download location"""
        return ("{}/{self.task.uuid}".format(reverse("api:api-v4-taskresult"), **locals()), 
                "Download results")

    def get_response(self):
        """Default: instantiate the script and ask it to provide response"""
        result = self.task._get_raw_result()
        if isinstance(result, dict) and result.get('type') == 'download':
            data = base64.b64decode(result['data'])
            response = HttpResponse(data, content_type=result['content_type'], status=200)
            response['Content-Disposition'] = 'attachment; filename="{filename}"'.format(**result)
            return response
        else:

            response = HttpResponse(result, content_type='application/json', status=200)
            return response

def get_temporary_file_dict(fo):
    """
    Creates a non-deleting, named, temporary file for `fo`.

    @type fo: method .chunks() should return list of list of bytes
    @rtype: string
    """
    with tempfile.NamedTemporaryFile(delete=False) as dest:
        for chunk in fo.chunks():
            dest.write(chunk)

    os.chmod(dest.name, 0o644)
    return {
        "filename": fo.name,
        "path": dest.name,
        "content_type": fo.content_type
    }

class ScriptMixin(FormMixin):
    script = None # plugin/script to base the view on

    def get_script(self):
        return self.script

    def get_form_class(self):
        return self.get_script().options_form

    def get_initial(self):
        initial = {k.replace("_id", ""): v for (k, v) in self.kwargs.items()}
        initial.update(super(ScriptMixin, self).get_initial())
        return initial

    def run_form_delayed(self, project, handler=ScriptHandler):
        """
        Run the given form as a celery task
        @param project: the context project
        @param handler: the handler (see amcat.models.Task)
        """
        # Get kwargs and deal with querydict lists (which json truncates since
        # it thinks it's a dict)
        kwargs = self.get_form_kwargs()
        if isinstance(kwargs.get('data'), QueryDict):
            kwargs['data'] = dict(kwargs['data'].lists())

        # Convert file objects to temporary filenames
        if isinstance(kwargs.get('files'), MultiValueDict):
            for key in kwargs['files'].keys():
                file_object_list = kwargs['files'].getlist(key)
                for i, fo in enumerate(file_object_list):
                    file_object_list[i] = get_temporary_file_dict(fo)
            kwargs['files'] = dict(kwargs['files'])

        task = handler.call(target_class=self.get_script(), arguments=kwargs,
                            project=project, user=self.request.user)
        url = reverse("navigator:task-details", args=[project.id, task.task.id])
        next = urlencode(dict(next=self.request.get_full_path()))
        return redirect("{url}?{next}".format(**locals()), permanent=False)

    def run_form(self, form):
        self.form = form
        self.script_object = self.get_script()(form)
        self.result =  self.script_object.run()
        self.success = True
        return self.result

    def form_valid(self, form):
        self.run_form(form)
        return super(ScriptMixin, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ScriptMixin, self).get_context_data(**kwargs)
        context['script'] = self.get_script()
        context['script_name'] = self.get_script().name # for some reason {{ script.name }} in a template instantiates script...
        return context


class ScriptView(ProcessFormView, ScriptMixin, TemplateResponseMixin):
    pass


class TableExportMixin():

    def export_filename(self, form):
        """Return the filename to export as (without extension)"""
        return self.__class__.__name__

    def get_form_class(self):

        class ExportFormWrapper(self.script.options_form):
            format = forms.ChoiceField(choices = [(k, v.name) for (k,v) in table3.EXPORTERS.items()],
                                       label = "Export format")
        return ExportFormWrapper

    def form_valid(self, form):
        table = self.get_script().run_script(form)
        exporter = table3.EXPORTERS[form.cleaned_data["format"]]
        filename = "{fn}.{exporter.extension}".format(fn=self.export_filename(form), **locals())
        response = HttpResponse(content_type='text/csv', status=200)
        response['Content-Disposition'] = 'attachment; filename="{filename}"'.format(**locals())
        exporter.export(table, stream = response)
        return response
