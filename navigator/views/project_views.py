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

from navigator.views.datatableview import DatatableMixin
from django.views.generic.list import ListView
from api.rest.datatable import FavouriteDatatable
from amcat.models import Project
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin

class ProjectListView(BreadCrumbMixin, DatatableMixin, ListView):
    model = Project
    context_category = 'Articles'
    template_name = "project/project_list.html"
    
    def get_context_data(self, **kwargs):
        context = super(ProjectListView, self).get_context_data(**kwargs)
        context["what"] = self.kwargs.get('what', 'favourites')
        context["main_active"] = 'Projects'
        return context

    def get_breadcrumbs(self):
        return [("Projects", "#")]

    def filter_table(self, table):
        what = self.kwargs.get('what', 'favourites')
        if what == 'favourites':
            # ugly solution - get project ids that are favourite and use that to filter, otherwise would have to add many to many to api?
            # (or use api request.user to add only current user's favourite status). But good enough for now...
            ids = self.request.user.get_profile().favourite_projects.all().values_list("id")
            ids = [id for (id, ) in ids]
            if ids: 
                return table.filter(pk=ids, active=True)
            else:
                return table.filter(name="This is a really stupid way to force an empty table (so sue me!)")
        elif what == "own":
            return table.filter(projectrole__user=self.request.user, active=True)
        elif what == "all":
            return table

        
    def get_datatable(self):
        """Create the Datatable object"""

        url = reverse('project', args=[123])
        table = FavouriteDatatable(resource=self.get_resource(), label="project",
                                   set_url=url + "?star=1", unset_url=url+"?star=0")
        table = table.rowlink_reverse('project', args=['{id}'])

        table = self.filter_table(table)
        return table
