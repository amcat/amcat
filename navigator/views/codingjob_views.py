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
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView, ProjectActionRedirectView, ProjectEditView, ProjectDetailView, ProjectFormView
from navigator.views.datatableview import DatatableMixin
from amcat.models import CodingJob
from navigator.utils.misc import session_pop
from navigator.views.project_views import ProjectDetailsView
from api.rest.resources import SearchResource

from amcat.scripts.actions.add_codingjob import AddCodingJob
from amcat.forms.widgets import convert_to_jquery_select
from django import forms
from django.core.urlresolvers import reverse

from amcat.scripts.actions.get_codingjob_results import CodingjobListForm, EXPORT_FORMATS, GetCodingJobResults
from django.utils.datastructures import SortedDict
import datetime
from django.http import HttpResponse
import json
from amcat.models import User

class CodingJobListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = CodingJob
    parent = ProjectDetailsView
    context_category = 'Coding'
    resource = CodingJobViewSet
    rowlink = './{id}'

    def get_datatable(self, **kwargs):
        url_kwargs = dict(project=self.project.id)
        return super(CodingJobListView, self).get_datatable(url_kwargs=url_kwargs, **kwargs)
    def filter_table(self, table):
        return table.hide("project", "articleset", "favourite")
   

    def get_context_data(self, **kwargs):
        ctx = super(CodingJobListView, self).get_context_data(**kwargs)

        deleted = session_pop(self.request.session, "deleted_codingjob")
        added = session_pop(self.request.session, "added_codingjob")
        if added:
            added = [CodingJob.objects.get(pk=i) for i in added]

        ctx.update(**locals())
        return ctx

class CodingJobDetailsView(ProjectDetailView, DatatableMixin):
    model = CodingJob
    parent = CodingJobListView
    resource = SearchResource
    rowlink = './{id}'
    
    def filter_table(self, table):
        table = table.filter(sets=self.object.articleset.id)
        table = table.rowlink_reverse('article-details', args=[self.project.id, self.object.articleset.id, '{id}'])
        return table


class CodingJobEditView(ProjectEditView):
    parent = CodingJobDetailsView
    fields = ['project', 'name', 'coder', 'unitschema', 'articleschema']
    

    def get_form(self, form_class):
        form = super(CodingJobEditView, self).get_form(form_class)
        form.fields['coder'].queryset = User.objects.filter(projectrole__project=self.project)
        form.fields['unitschema'].queryset = self.project.get_codingschemas().filter(isarticleschema=False)
        form.fields['articleschema'].queryset = self.project.get_codingschemas().filter(isarticleschema=True)
        
        return form
        
class CodingJobAddView(ProjectScriptView):
    parent = CodingJobListView
    script = AddCodingJob
    url_fragment = "add"

    def run_form(self, form):
        result = super(CodingJobAddView, self).run_form(form)
        if isinstance(result, CodingJob): result = [result]
        self.request.session['added_codingjob'] = [job.id for job in result]
        return result

    def get_form_kwargs(self):
        kwargs = super(CodingJobAddView, self).get_form_kwargs()
        kwargs['project'] = self.project
        return kwargs
    
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
        CodingJob.objects.get(pk=codingjob_id).recycle()
        
    def get_redirect_url(self, **kwargs):
        return CodingJobListView._get_breadcrumb_url(kwargs, self)

class CodingJobExportSelectView(ProjectFormView):
    form_class = CodingjobListForm
    parent = CodingJobListView
    url_fragment = "export-select"

    def get_form_kwargs(self):
        kwargs = super(CodingJobExportSelectView, self).get_form_kwargs()
        kwargs.update(project=self.project)
        return kwargs

    def form_valid(self, form):
        self.jobs = form.cleaned_data["codingjobs"]
        self.level = form.cleaned_data["export_level"]
        return super(CodingJobExportSelectView, self).form_valid(form)
    
    def get_success_url(self):
        url = reverse(CodingJobExportView.get_view_name(), args=[self.project.id])
        if len(self.jobs) < 100:
            codingjobs_url = "&".join("codingjobs={}".format(c.id) for c in self.jobs)
        else:
            codingjobs_url = "use_session=1"
            self.request.session['export_job_ids'] = json.dumps([c.id for c in self.jobs])
            
        return "{url}?export_level={self.level}&{codingjobs_url}".format(**locals())
    
class CodingJobExportView(ProjectScriptView):
    script = GetCodingJobResults
    parent = CodingJobListView
    url_fragment = "export"
    template_name = "project/coding_job_export.html"

    def read_get(self):
        if self.request.GET.get("use_session"):
            jobs = json.loads(self.request.session['export_job_ids'])
        else:
            jobs = self.request.GET.getlist("codingjobs")
        level = int(self.request.GET["export_level"])
        return jobs, level
    
    def get_form_kwargs(self):
        kwargs = super(CodingJobExportView, self).get_form_kwargs()
        jobs, level = self.read_get()
        kwargs.update(dict(project=self.project, codingjobs=jobs, export_level=level))
        return kwargs

    def get_initial(self):
        jobs, level = self.read_get()
        return dict(codingjobs=jobs, export_level=level)

    def get_context_data(self, form, **kwargs):
        context = super(CodingJobExportView, self).get_context_data(form=form, **kwargs)

        # add fields for schema fields
        sections = SortedDict() # section : [(id, field, subfields) ..]
        subfields = {} # fieldname -> subfields reference

        for name in form.fields:
            if form[name].is_hidden:
                continue
            prefix = name.split("_")[0]
            section = {"schemafield" : "Field options", "meta" : "Metadata options"}.get(prefix, "General options")

            if prefix == "schemafield" and not name.endswith("_included"):
                continue
            subfields[name] = []
            sections.setdefault(section, []).append((name, form[name], subfields[name]))

        # sort coding fields
        codingfields = sorted(sections["Field options"])
        sections["Field options"].sort()

        for name in form.fields: # add subordinate fields        
            prefix = name.split("_")[0]
            if prefix == "schemafield" and not name.endswith("_included"):
                subfields[name.rsplit("_", 1)[0] + "_included"].append((name, form[name]))

        for flds in subfields.values():
            flds.sort()
            
        context['sections'] = sections
        return context

    def form_valid(self, form):
        results = self.run_form(form)
        eformat = {f.label : f for f in EXPORT_FORMATS}[form.cleaned_data["export_format"]]
        jobs = form.cleaned_data["codingjobs"]
        if eformat.mimetype is not None:
            if len(jobs) > 3:
                jobs = jobs[:3] + ["etc"]
            filename = "Codingjobs {j} {now}.{ext}".format(j=",".join(str(j) for j in jobs), now=datetime.datetime.now(), ext=eformat.label)
            response = HttpResponse(content_type=eformat.mimetype, status=200)
            response['Content-Disposition'] = 'attachment; filename="{filename}"'.format(**locals())
            response.write(results)
            return response
