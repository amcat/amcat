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

from django.views.generic.edit import FormMixin, ProcessFormView
from django.views.generic.base import TemplateResponseMixin

from django.forms.widgets import HiddenInput

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django import forms

from navigator.utils.auth import check
from amcat.models import Project
from amcat.tools.table import table3

class ScriptMixin(FormMixin):
    script = None # plugin/script to base the view on

    def get_script(self):
        return self.script
    
    def get_form_class(self):
        return self.get_script().options_form
    
    def form_valid(self, form):
        self.form = form
        self.result = self.get_script().run_script(form)
        return super(ScriptMixin, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ScriptMixin, self).get_context_data(**kwargs)
        context['script'] = self.get_script()
        context['script_name'] = self.get_script().name # for some reason {{ script.name }} in a template instantiates script...
        return context
    

class ScriptView(ProcessFormView, ScriptMixin, TemplateResponseMixin):
    pass

class ProjectScriptView(ScriptView):
    """
    View that provides access to a Script from within a plugin.
    Subclasses should provide a script instance.
    """
    template_name = "navigator/project/script_base.html"

    def get_initial(self):
        initial = super(ProjectScriptView, self).get_initial()
        initial["project"] = self.project
        return initial
        
    def get_success_url(self):
        return reverse("project", kwargs=dict(id=self.project.id))
        
    def get_form(self, form_class):
        form = super(ScriptView, self).get_form(form_class)
        if self.request.method == 'GET':
            for key, val in self.url_data.iteritems():
                if key in form.fields:
                    form.fields[key].initial = val
            if 'project' in form.fields:
                form.fields['project'].widget = HiddenInput()
        return form

    def _initialize_url_data(self, **kwargs):
        self.project = Project.objects.get(pk=kwargs["projectid"])
        self.url_data = kwargs
    
    def post(self, request, **kwargs):
        self._initialize_url_data(**kwargs)
        return super(ProjectScriptView, self).post(request, **kwargs)
                
    def get(self, request, **kwargs):
        self._initialize_url_data(**kwargs)
        return super(ProjectScriptView, self).get(request, **kwargs)
        
    def get_context_data(self, **kwargs):
        context = super(ProjectScriptView, self).get_context_data(**kwargs)
        context["project"] = self.project
        context["script_doc"] = self.script.__doc__.strip()
        return context

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
