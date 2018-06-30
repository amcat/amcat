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
from copy import copy

from rest_framework.decorators import api_view
from django.http import HttpResponse

from amcat.models.task import Task, TaskPending
from api.rest.resources.amcatresource import AmCATResource
from api.rest.viewsets.task import TaskSerializer, TaskResultSerializer


class TaskResource(AmCATResource):
    model = Task
    serializer_class = TaskSerializer
    queryset = Task.objects.all()
    ignore_filters = ("arguments",)

#TODO: WvA: Isn't it redundant to have both taskresult and single_task_result?
class TaskResultResource(AmCATResource):
    model = Task
    ignore_filters = ("arguments",)

    @classmethod
    def get_model_name(cls):
        return "taskresult"

    serializer_class = TaskResultSerializer
    
@api_view(http_method_names=("GET",))
def single_task_result(request, task_id, uuid=False):
    task = Task.objects.get(**{ "uuid" if uuid else "id" : task_id})
    try:
        return copy(task.get_handler().get_response())
    except TaskPending:
        return HttpResponse(status=404)
    except Exception as e:
        if e.__class__.__name__ in ('QueryValidationError', 'QueryError', 'QueryParseError'):
            error_msg= "Cannot parse query: {e}".format(e=e.message)

        else:
            error_msg = "{e.__class__.__name__}: {e}".format(**locals())
        return HttpResponse(content=error_msg, status=500)
