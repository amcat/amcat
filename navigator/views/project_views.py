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

from django.core.urlresolvers import reverse
from django.views.generic.list import ListView
from django.views.generic.edit import UpdateView

from amcat.forms.widgets import BootstrapMultipleSelect
from amcat.scripts.article_upload.upload_plugins import get_project_plugins, get_upload_plugins
from navigator.views.datatableview import DatatableMixin
from amcat.models import Project, ArticleSet
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin
from navigator.views.scriptview import ScriptView
from amcat.scripts.actions.add_project import AddProject

from amcat.tools.usage import log_request_usage

from api.rest import resources

class ProjectListView(BreadCrumbMixin, DatatableMixin, ListView):
    model = Project
    template_name = "project/project_list.html"

    def get(self, *args, **kargs):
        favaction = self.request.GET.get('favaction')
        if (favaction is not None):
            ids = {int(id) for id in self.request.GET.getlist('ids')}
            favs = self.request.user.userprofile.favourite_projects
            favids = set(favs.values_list("pk", flat=True))
            if favaction == "setfav":
                ids -= favids
                func = favs.add
            else:
                ids &= favids
                func = favs.remove
            if ids:
                [func(id) for id in ids]

        return super(ProjectListView, self).get(*args, **kargs)


    def get_datatable_kwargs(self):
        return {"checkboxes": True}

    def get_context_data(self, **kwargs):
        context = super(ProjectListView, self).get_context_data(**kwargs)
        context["what"] = self.what
        context["favaction"] = "unsetfav" if self.what == 'active' else "setfav"
        context["main_active"] = 'Projects'
        return context

    def get_breadcrumbs(self):
        return [("Projects", "#")]

    @property
    def what(self):
        if self.request.user.is_anonymous():
            return 'all'
        else:
            return self.kwargs.get('what', 'active')
    
    def filter_table(self, table):
        table = table.rowlink_reverse('navigator:articleset-list', args=['{id}'])
        if self.what == 'all':
            return table

        # ugly solution - get project ids that are favourite and use that to filter, otherwise would have to add many to many to api?
        # (or use api request.user to add only current user's favourite status). But good enough for now...
        table = table.hide('favourite', 'active')
        favids = self.request.user.userprofile.favourite_projects.all()
        favids = favids.values_list("id", flat=True)
        if self.what == 'active':
            ids = favids
        else:
            ids = Project.objects.filter(projectrole__user=self.request.user).exclude(pk__in=favids)
            ids = ids.values_list("id", flat=True)

        if ids:
            return table.filter(pk=ids, active=True)
        else:
            return table.filter(name="This is a really stupid way to force an empty table (so sue me!)")


from django import forms
from amcat.models import Role
class ProjectDetailsView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, UpdateView):
    context_category = 'Settings'
    parent = None
    base_url = "projects"
    model = Project

    def get_success_url(self):
        return reverse("navigator:{}".format(self.get_view_name()), args=(self.project.id,))


    @classmethod
    def _get_breadcrumb_url(cls, kwargs, view):
        return reverse("navigator:articleset-list", args=(kwargs['project'],))

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.initial['upload_plugins'] = [k for k, v in get_project_plugins(self.project).items()]
        form.fields['display_properties'].choices = [(k, k) for k in self.project.get_used_properties()]
        x = self.project.get_used_properties()
        return form

    def form_valid(self, form:forms.Form):
        response = super().form_valid(form)
        for name, enabled in form.cleaned_data['upload_plugins'].items():
            self.project.upload_plugins.update_or_create(name=name, defaults={"enabled": enabled})
        return response

    class form_class(forms.ModelForm):
        class Meta:
            model = Project
            exclude = ('codingschemas', 'codebooks', 'articlesets', 'favourite_articlesets')
        guest_role = forms.ModelChoiceField(queryset=Role.objects.all(), required=False,
                                            help_text="What level of access should people who are not added to the "
                                            "project have? If you select None, the project and its contents will "
                                            "not be visible to non-members")
        upload_plugins = forms.MultipleChoiceField(choices=[(k, v.label) for k, v in get_upload_plugins().items()],
                                                   widget=BootstrapMultipleSelect)

        display_properties = forms.MultipleChoiceField(choices=[], widget=BootstrapMultipleSelect, required=False)

        def clean_upload_plugins(self):
            plugins = {f: False for f, _ in self.fields['upload_plugins'].choices}
            plugins.update({f: True for f in self.cleaned_data['upload_plugins']})
            return plugins

        def clean_display_properties(self):
            if not self.cleaned_data['display_properties']:
                return []
            return self.cleaned_data['display_properties']


class ProjectAddView(BreadCrumbMixin, ScriptView):
    template_name = "script_base.html"
    script = AddProject
    model = Project

    def get_context_data(self, **kwargs):
        context = super(ProjectAddView, self).get_context_data(**kwargs)
        context["cancel_url"] = reverse("navigator:projects")
        context["script_doc"] = (self.script.__doc__ and self.script.__doc__.replace("   ", ""))
        return context

    def get_form(self, form_class=None):
        if self.request.method == 'GET':
            if form_class is None:
                form_class = self.get_form_class()
            return form_class.get_empty(user=self.request.user)
        else:
            return super(ProjectAddView, self).get_form(form_class)

    def get_success_url(self):
        log_request_usage(self.request, "project", "create", self.result)
        return reverse('navigator:articleset-list', args=[self.result.id])
