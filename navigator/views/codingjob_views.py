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
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView, ProjectActionRedirectView, ProjectEditView
from navigator.views.datatableview import DatatableMixin
from amcat.models import CodingJob
from navigator.utils.misc import session_pop
from navigator.views.project_views import ProjectDetailsView
from django.views.generic.detail import DetailView
from api.rest.resources import  ArticleMetaResource
from amcat.models.user import LITTER_USER_ID
from amcat.models.project import LITTER_PROJECT_ID

class CodingJobListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = CodingJob
    parent = ProjectDetailsView
    context_category = 'Coding'
    resource = CodingJobViewSet
    rowlink = './{id}'

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

class CodingJobDetailsView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DatatableMixin, DetailView):
    model = CodingJob
    parent = CodingJobListView
    resource = ArticleMetaResource

    def filter_table(self, table):
        return (table.filter(articleset=self.object.articleset.id)
                .hide("section", "pagenr", "byline", "metastring", "url")
                .hide("project", "medium", "text", "uuid"))



class CodingJobEditView(ProjectEditView):
    parent = CodingJobDetailsView
    fields = ['project', 'name', 'coder', 'unitschema', 'articleschema']
    
from amcat.scripts.actions.add_codingjob import AddCodingJob
from amcat.forms.widgets import convert_to_jquery_select
from django import forms

class CodingJobAddView(ProjectScriptView):
    parent = CodingJobListView
    script = AddCodingJob
    url_fragment = "add"

    def run_form(self, form):
        result = super(CodingJobAddView, self).run_form(form)
        if isinstance(result, CodingJob): result = [result]
        self.request.session['added_codingjob'] = [job.id for job in result]
        return result
    
    def get_form(self, form_class):
        form = super(CodingJobAddView, self).get_form(form_class)
        form.fields['insertuser'].initial = self.request.user
        form.fields["insertuser"].widget = forms.HiddenInput()
        convert_to_jquery_select(form)
        return form

class CodingJobDeleteView(ProjectActionRedirectView):
    parent = CodingJobDetailsView
    url_fragment = "delete"

    def action(self, project_id, codingjob_id):
        codingjob = CodingJob.objects.get(pk=codingjob_id)
        codingjob.project_id = LITTER_PROJECT_ID
        codingjob.coder_id = LITTER_USER_ID
        codingjob.save()
        
    def get_redirect_url(self, **kwargs):
        return CodingJobListView._get_breadcrumb_url(kwargs, self)
