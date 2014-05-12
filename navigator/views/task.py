###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                        #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################
from django.views.generic import ListView, DetailView
from amcat.models import Task
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import ProjectViewMixin, BreadCrumbMixin, HierarchicalViewMixin, ProjectDetailView


class TaskListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, ListView):
    model = Task
    parent = ProjectDetailsView

class TaskDetailsView(ProjectDetailView):
    parent = TaskListView
    model = Task

    def get_context_data(self, **kwargs):
        async_result = self.object.get_async_result()
        next = self.request.GET.get("next")
        return super(TaskDetailsView, self).get_context_data(async_result=async_result, next=next, **kwargs)

