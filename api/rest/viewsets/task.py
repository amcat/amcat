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

from amcat.models.task import IN_PROGRESS, FAILED
from amcat.models import Task
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin, UUIDLookupMixin
from rest_framework.viewsets import ModelViewSet
from api.rest.mixins import DatatablesMixin


__all__ = ("TaskSerializer", "TaskResultSerializer", "TaskViewSet")

class TaskSerializer(AmCATModelSerializer):
    """Represents a Task object defined in amcat.models.task.Task. Adds two
    fields to the model: status and ready."""
    description = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    ready = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    redirect_url = serializers.SerializerMethodField()
    redirect_message = serializers.SerializerMethodField()
    uuid = serializers.SerializerMethodField()
    error = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(TaskSerializer, self).__init__(*args, **kwargs)
        self._tasks = {}

    def set_status_ready(self, task):
        async = task.get_async_result()
        self._tasks[task] = (async.ready(), async.result, async.status)

    def get_status_ready(self, task):
        """Returns tuple with (status, ready) => (str, bool)"""
        if task not in self._tasks:
            self.set_status_ready(task)
        return self._tasks[task]

    def get_status(self, task):
        _, _, status = self.get_status_ready(task)
        return status

    def get_ready(self, task):
        ready, _, _ = self.get_status_ready(task)
        return ready

    def get_progress(self, task):
        _, result, status = self.get_status_ready(task)
        if status == IN_PROGRESS and isinstance(result, dict):
            return result

    def get_description(self, task):
        return task.class_name.split(".")[-1]

    def _get_redirect(self, task):
        ready, _, status = self.get_status_ready(task)
        if ready and status != FAILED:
            return task.get_handler().get_redirect()

    def get_redirect_url(self, task):
        redirect = self._get_redirect(task)
        if redirect:
            return redirect[0]

    def get_redirect_message(self, task):
        redirect = self._get_redirect(task)
        if redirect:
            return redirect[1]

    def get_uuid(self, task):
        return str(task.uuid)

    def get_error(self, task):
        _, result, status = self.get_status_ready(task)
        if status == FAILED:
            return result


          
    def save(self, **kwargs):
        from amcat.models.task import amcat_task
        task = super(TaskSerializer, self).save(**kwargs)
        amcat_task.apply_async(task_id=str(task.uuid))
        return task
        
class TaskResultSerializer(AmCATModelSerializer):
    result = serializers.SerializerMethodField()
    ready = serializers.SerializerMethodField()

    def get_ready(self, task):
        return task.ready

    def get_result(self, task):
        if not self.get_ready(task):
            return None
        return task.get_result()

    class Meta:
        model = Task
        fields = ("uuid", "ready", "result")


       
class TaskViewSet(AmCATViewSetMixin, UUIDLookupMixin, DatatablesMixin, ModelViewSet):
    model = Task
    serializer_class = TaskSerializer
    queryset = Task.objects.all()
    model_key = "task"
    ignore_filters = ("arguments", )
