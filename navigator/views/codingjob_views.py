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
from django.views.generic.list import ListView

from api.rest.viewsets import CodingJobViewSet
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView
from navigator.views.datatableview import DatatableMixin
from amcat.models import CodingJob
from navigator.utils.misc import session_pop
from navigator.views.project_views import ProjectDetailsView


class CodingJobListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = CodingJob
    parent = ProjectDetailsView
    context_category = 'Coding'
    resource = CodingJobViewSet

    def get_datatable(self, **kwargs):
        url_kwargs = dict(project=self.project.id)
        return super(CodingJobListView, self).get_datatable(url_kwargs=url_kwargs, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(CodingJobListView, self).get_context_data(**kwargs)

        deleted = session_pop(self.request.session, "deleted_codingjob")
        added = session_pop(self.request.session, "added_codingjob")
        if added:
            added = [CodingJob.objects.get(pk=i) for i in added]

        ctx.update(**locals())
        return ctx

from amcat.scripts.actions.add_codingjob import AddCodingJob
from amcat.forms.widgets import convert_to_jquery_select
from django import forms

class CodingJobAddView(ProjectScriptView):
    parent = CodingJobListView
    script = AddCodingJob
    url_fragment = "add"
    
    def get_success_url(self):
        result = self.result
        if isinstance(result, CodingJob): result = [result]
        request.session['added_codingjob'] = [job.id for job in result]
        return reverse("coding job-list", args=[project.id])
        
    def get_form(self, form_class):
        form = super(CodingJobAddView, self).get_form(form_class)
        form.fields['insertuser'].initial = self.request.user
        form.fields["insertuser"].widget = forms.HiddenInput()
        convert_to_jquery_select(form)
        return form
