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
from rest_framework import serializers
from rest_framework.decorators import api_view
from amcat.models import Task

from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer

class TaskSerializer(AmCATModelSerializer):
    """Represents a Task object defined in amcat.models.task.Task. Adds two
    fields to the model: status and ready."""
    status = serializers.SerializerMethodField('get_status')
    ready = serializers.SerializerMethodField('get_ready')

    def get_status(self, task):
        return task.get_async_result().status

    def get_ready(self, task):
        return task.get_async_result().ready()

    class Meta:
        model = Task

class TaskResource(AmCATResource):
    model = Task
    serializer_class = TaskSerializer

class TaskResultSerializer(AmCATModelSerializer):
    result = serializers.SerializerMethodField('get_result')
    ready = serializers.SerializerMethodField('get_ready')

    def get_ready(self, task):
        return task.get_async_result().ready()

    def get_result(self, task):
        if not self.get_ready(task):
            return None
        return task.get_result()

    class Meta:
        model = Task
        fields = ("uuid", "ready", "result")


class TaskResultResource(AmCATResource):
    model = Task

    @classmethod
    def get_model_name(cls):
        return "taskresult"

    serializer_class = TaskResultSerializer


