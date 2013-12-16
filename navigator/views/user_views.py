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

from django.core.urlresolvers import reverse

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView
from navigator.views.datatableview import DatatableMixin
from amcat.models import User
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import UpdateView

from django.views.generic.base import RedirectView
from api.rest.resources import ProjectRoleResource

class UserListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = User
    parent = None
    base_url = "projects/(?P<project_id>[0-9]+)"
    context_category = 'Settings'

    resource = ProjectRoleResource
    rowlink = './{id}'
    @classmethod
    def get_view_name(cls):
        return "user-list"

    url_fragment = "users"
        
    def filter_table(self, table):
        return table.filter(project=self.project).hide('project', 'id')
#    if request.user.get_profile().haspriv('manage_project_users', project):
#        add_user = forms.ProjectRoleForm(project)
