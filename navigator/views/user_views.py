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

from django import forms
from django.core.urlresolvers import reverse
from django.views.generic.base import RedirectView
from django.views.generic.list import ListView

from amcat.forms.widgets import BootstrapMultipleSelect
from amcat.models import Project, ProjectRole, Role
from amcat.models import User, authorisation
from api.rest.resources import ProjectRoleResource
from navigator.forms import gen_user_choices
from navigator.views.datatableview import DatatableMixin
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin

class ProjectRoleForm(forms.ModelForm):
    user = forms.MultipleChoiceField(widget=BootstrapMultipleSelect)

    def __init__(self, project=None, user=None, data=None, **kwargs):
        super(ProjectRoleForm, self).__init__(data=data, **kwargs)

        self.fields['user'].choices = gen_user_choices()

        if project is not None:
            # Disable self.project
            del self.fields['project']

            choices = [(r.id, r.label) for r in Role.objects.filter(projectlevel=True)] + [(None, "Remove user")]
            self.fields['role'].choices = choices

            if user is not None:
                del self.fields['user']

    class Meta:
        model = ProjectRole
        exclude = ()


class ProjectUserListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = User
    parent = None
    base_url = "projects/(?P<project>[0-9]+)"
    context_category = 'Settings'
    url_fragment = "users"
    resource = ProjectRoleResource

    @classmethod
    def get_view_name(cls):
        return "user-list"

    def get_context_data(self, **kwargs):
        context = super(ProjectUserListView, self).get_context_data(**kwargs)
        context['add_user'] = ProjectRoleForm(self.project)
        return context

    def filter_table(self, table):
        return table.filter(project=self.project).hide('project', 'id')


class ProjectUserAddView(ProjectViewMixin, HierarchicalViewMixin, RedirectView):
    required_project_permission = authorisation.ROLE_PROJECT_ADMIN
    parent = ProjectUserListView
    url_fragment = "add"
    model = User

    def get_redirect_url(self, project):
        project = Project.objects.get(id=project)
        role = self.request.POST['role']
        role = None if role == 'None' or role == "" else Role.objects.get(id=role, projectlevel=True)
        for user in User.objects.filter(id__in=self.request.REQUEST.getlist('user')):
            try:
                r = ProjectRole.objects.get(project=project, user=user)
                if role is None:
                    r.delete()
                else:
                    r.role = role
                    r.save()
            except ProjectRole.DoesNotExist:
                if role is not None:
                    r = ProjectRole(project=project, user=user, role=role)
                    r.save()
        return reverse("navigator:user-list", args=[project.id])
