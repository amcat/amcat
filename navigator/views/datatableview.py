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

from django.views.generic.base import ContextMixin, TemplateResponseMixin, TemplateView
from django.views.generic.edit import CreateView
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory


from api.rest import resources
from api.rest.datatable import Datatable


class DatatableMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super(DatatableMixin, self).get_context_data(**kwargs)
        context["model"] = getattr(self, "model", None)
        context["model_name"] = self.model.__name__ if hasattr(self, "model") else None
        context["table"] = self.get_datatable()
        return context

    
    def get_datatable(self):
        """Create the Datatable object"""
        table = Datatable(self.get_resource(), rowlink=self.get_rowlink())
        table = self.filter_table(table)
        return table

    def get_resource(self):
        """Return the rest API resource (View) for the data table"""
        try:
            return self.resource
        except AttributeError:
            model = self.model
            return resources.get_resource_for_model(model)

    def filter_table(self, table):
        """Perform any needed postprocessing on the table and return it"""
        return table
    
    def get_rowlink(self):
        try:
            return self.rowlink
        except AttributeError:
            try:
                urlname = self.rowlink_urlname
            except AttributeError:
                return None
            else:
                return reverse(urlname, args=[999]).replace("999", "{id}")
            
        return getattr(self, "rowlink", None)

class DatatableView(TemplateView, DatatableMixin):
    template_name = "datatable.html"

class DatatableCreateView(CreateView, DatatableMixin):
    template_name = "datatable.html"
    
    def get_form_class(self):
        form_class = getattr(self, "form_class", None)
        if form_class is None:
            form_class =  modelform_factory(self.model)
        return form_class

    def get_success_url(self):
        try:
            urlname = self.rowlink_urlname
        except AttributeError:
            return super(DatatableCreateView, self).get_success_url()
        else:
            return reverse(urlname, args=[self.object.pk])
        
