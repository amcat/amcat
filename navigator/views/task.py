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
from operator import attrgetter
from datetime import timedelta, datetime
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.views.generic import ListView, DetailView
from amcat.models import Task
from api.rest.resources import TaskResource
from navigator.utils import set_notice
from navigator.views.datatableview import DatatableMixin
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import ProjectViewMixin, BreadCrumbMixin, HierarchicalViewMixin, ProjectDetailView

def clean_ready(request, project_id):
    """Deletes task objects which property 'ready' is True."""
    tasks = Task.objects.filter(project__id=project_id, user=request.user)
    finished_tasks = filter(attrgetter("ready"), tasks)
    finished_tasks = Task.objects.filter(id__in=(t.id for t in finished_tasks))
    finished_tasks_count = finished_tasks.count()
    finished_tasks.delete()
    set_notice(request, title='Cleaned', text='Deleted %s task(s).' % finished_tasks_count)
    return redirect(request.META["HTTP_REFERER"], permanent=False)

def clean_stuck(request, project_id):
    """Deletes task objects which are older than 24 hours."""
    one_day_ago = datetime.now() - timedelta(days=1)
    tasks = Task.objects.filter(project__id=project_id, user=request.user, issued_at__lte=one_day_ago)
    tasks_count = tasks.count()
    tasks.delete()
    set_notice(request, title="Cleaned", text="Deleted %s task(s)." % tasks_count)
    return redirect(request.META["HTTP_REFERER"], permanent=False)

def uuid_redirect(request, project_id, uuid):
    task_id = Task.objects.get(uuid=uuid.lower()).id
    return redirect(reverse("task-details", args=[project_id, task_id]), permanent=True)

class TaskListView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = Task
    parent = ProjectDetailsView
    context_category = 'Tasks'
    rowlink = './{id}'

    @classmethod
    def get_url_patterns(cls):
        patterns = list(super(TaskListView, cls).get_url_patterns())
        patterns.append(patterns[0][:-1] + "(?P<what>|own|project)?/?$")
        return patterns

    @property
    def what(self):
        return self.kwargs.get("what", "own")

    def get_context_data(self, **kwargs):
        context = super(TaskListView, self).get_context_data(**kwargs)
        tables = [("own", "My tasks"), ("project", "Project tasks")]
        return dict(context, what=self.what, **locals())

    def filter_project_table(self, table):
        return table.filter(project=self.project)

    def filter_own_table(self, table):
        return table.filter(project=self.project, user=self.request.user)

    def get_resource(self):
        return TaskResource

    def filter_table(self, table):
        return getattr(self, "filter_{}_table".format(self.what), lambda t: t)(table)

    def get_datatable(self, **kwargs):
        table = super(TaskListView, self).get_datatable(**kwargs)
        return table.hide(
            "uuid", "project", "called_with", "persistent", "progress",
            "task_name", "class_name"
        )

class TaskDetailsView(ProjectDetailView):
    parent = TaskListView
    model = Task


    @classmethod
    def _get_breadcrumb_name(cls, kwargs, view):
        obj = cls._get_object(kwargs)
        name = obj.class_name.split(".")[-1]
        return "{obj.id} : {name}".format(**locals())

    def get_context_data(self, **kwargs):
        async_result = self.object.get_async_result()
        next = self.request.GET.get("next")
        return super(TaskDetailsView, self).get_context_data(async_result=async_result, next=next, **kwargs)
