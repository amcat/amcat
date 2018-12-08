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
import json
from collections import OrderedDict

from django.views.generic.list import ListView
from django import forms
from django.core.urlresolvers import reverse

from amcat.forms.fields import StaticModelChoiceField
from api.rest.viewsets import CodingJobViewSet
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView, ProjectActionRedirectView, ProjectEditView, ProjectDetailView, ProjectFormView
from navigator.views.datatableview import DatatableMixin
from amcat.models import CodingJob
from navigator.utils.misc import session_pop
from navigator.views.project_views import ProjectDetailsView
from api.rest.resources import SearchResource
from amcat.scripts.actions.add_codingjob import AddCodingJob
from amcat.forms.widgets import convert_to_bootstrap_select
from amcat.scripts.actions.get_codingjob_results import CodingjobListForm, GetCodingJobResults
from amcat.models import User

SECTIONS = {
    "schemafield": "Field options",
    "aggregation": "Aggregation options",
    "meta": "Metadata options"
}

class CodingJobListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = CodingJob
    parent = ProjectDetailsView
    context_category = 'Coding'
    resource = CodingJobViewSet
    rowlink = './{id}'

    def get(self, *args, **kargs):
        favaction = self.request.GET.get('favaction')
        if (favaction is not None):
            ids = {int(id) for id in self.request.GET.getlist('ids')}
            CodingJob.objects.filter(pk__in=ids).update(archived=(favaction != "setfav"))

        return super(CodingJobListView, self).get(*args, **kargs)

    @property
    def what(self):
        return self.kwargs.get("what", "active")

    @classmethod
    def get_url_patterns(cls):
        patterns = list(super(CodingJobListView, cls).get_url_patterns())
        patterns.append(patterns[0][:-1] + "(?P<what>|active|archived)?/?$")
        return patterns

    def get_datatable(self, **kwargs):
        url_kwargs = dict(project=self.project.id)
        return super(CodingJobListView, self).get_datatable(url_kwargs=url_kwargs, **kwargs)

    def filter_table(self, table):
        table = table.filter(archived=(self.what != "active"))
        return table.hide("project", "articleset", "favourite")

    def get_datatable_kwargs(self):
        return {"checkboxes": True}

    def get_context_data(self, **kwargs):
        ctx = super(CodingJobListView, self).get_context_data(**kwargs)

        deleted = session_pop(self.request.session, "deleted_codingjob")
        added = session_pop(self.request.session, "added_codingjob")
        if added:
            added = [CodingJob.objects.get(pk=i) for i in added]
        what = self.what
        favaction = "unsetfav" if what == 'active' else "setfav"
        ctx.update(**locals())
        return ctx

class CodingJobDetailsView(ProjectDetailView, DatatableMixin):
    model = CodingJob
    parent = CodingJobListView
    resource = SearchResource
    rowlink = './{id}'

    def filter_table(self, table):
        table = table.filter(sets=self.object.articleset.id)
        table = table.filter(project=self.project.id)
        table = table.rowlink_reverse('navigator:article-details', args=[self.project.id, self.object.articleset.id, '{id}'])
        return table

    def get_datatable_kwargs(self):
        fields = [("col", prop) for prop in ("title", "date", "url")]
        used_props = self.object.articleset.get_used_properties()
        display_cols = self.project.get_display_columns()
        props = [("col", prop) for prop in display_cols if prop in used_props]
        return {"extra_args": fields + props}

class CodingJobEditView(ProjectEditView):
    parent = CodingJobDetailsView
    fields = ['project', 'name', 'coder', 'unitschema', 'articleschema']


    def get_form(self, form_class=None):
        form = super(CodingJobEditView, self).get_form(form_class)
        form.fields['coder'].queryset = User.objects.filter(projectrole__project=self.project)
        form.fields['unitschema'].queryset = self.project.get_codingschemas().filter(isarticleschema=False)
        form.fields['articleschema'].queryset = self.project.get_codingschemas().filter(isarticleschema=True)

        return form

class CodingJobAddView(ProjectScriptView):
    parent = CodingJobListView
    script = AddCodingJob
    url_fragment = "add"

    def get_context_data(self, **kwargs):
        context = super(CodingJobAddView, self).get_context_data(**kwargs)
        return context
        
    def run_form(self, form):
        result = super(CodingJobAddView, self).run_form(form)
        if isinstance(result, CodingJob): result = [result]
        self.request.session['added_codingjob'] = [job.id for job in result]
        return result

    def get_form_kwargs(self):
        kwargs = super(CodingJobAddView, self).get_form_kwargs()
        kwargs['project'] = self.project
        return kwargs

    def get_form(self, form_class=None):
        form = super(CodingJobAddView, self).get_form(form_class)
        form.fields['insertuser'] = StaticModelChoiceField(self.request.user)
        convert_to_bootstrap_select(form)
        return form

class CodingJobDeleteView(ProjectActionRedirectView):
    parent = CodingJobDetailsView
    url_fragment = "delete"

    def action(self, project, codingjob):
        CodingJob.objects.get(pk=codingjob).recycle()

    def get_success_url(self, **kargs):
        return reverse(CodingJobListView.get_view_name(), args=[self.project.id])

class CodingJobExportSelectView(ProjectFormView):
    form_class = CodingjobListForm
    parent = CodingJobListView
    url_fragment = "export-select"

    def get_form_kwargs(self):
        kwargs = super(CodingJobExportSelectView, self).get_form_kwargs()
        kwargs.update(project=self.project)

        if "data" in kwargs and "codingjobs" not in kwargs["data"]:
            archived = kwargs['data']['what'] != 'active'
            all_jobs = self.project.codingjob_set.filter(archived=archived).values_list("id", flat=True)
            kwargs["data"] = kwargs["data"].copy()
            kwargs["data"].setlist("codingjobs", all_jobs)

        return kwargs

    def form_valid(self, form):
        self.jobs = form.cleaned_data["codingjobs"]
        self.level = form.cleaned_data["export_level"]
        return super(CodingJobExportSelectView, self).form_valid(form)

    def get_success_url(self):
        url = reverse("navigator:" + CodingJobExportView.get_view_name(), args=[self.project.id])
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
    template_name = "project/codingjob_export.html"

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
        kwargs.update(dict(project=self.project.id, codingjobs=jobs, export_level=level))
        return kwargs

    def get_initial(self):
        jobs, level = self.read_get()
        return dict(codingjobs=jobs, export_level=level)

    def get_context_data(self, **kwargs):
        context = super(CodingJobExportView, self).get_context_data(**kwargs)
        form = self.get_form()

        # Add fields for schema fields
        # section : [(id, field, subfields) ..]
        sections = OrderedDict()

        # fieldname -> subfields reference
        subfields = {}

        for name in form.fields:
            if form[name].is_hidden:
                continue

            prefix = name.split("_")[0]
            section = SECTIONS.get(prefix, "General options")

            if prefix == "schemafield" and not name.endswith("_included"):
                continue

            subfields[name] = []
            sections.setdefault(section, []).append((name, form[name], subfields[name]))

        # Sort coding fields
        if 'Field options' in sections:
            sections["Field options"].sort()

        # Add subordinate fields
        for name in form.fields:
            prefix = name.split("_")[0]
            if prefix == "schemafield" and not name.endswith("_included"):
                subfields[name.rsplit("_", 1)[0] + "_included"].append((name, form[name]))

        for flds in subfields.values():
            flds.sort()

        context['sections'] = sections
        return context

    def form_valid(self, form):
        return self.run_form_delayed(self.project)
