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

    def get_initial(self):
        initial = {k.replace("_id", "")  : v for (k,v) in self.kwargs.iteritems()}
        initial.update(super(ScriptMixin, self).get_initial())
        return initial
                
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
