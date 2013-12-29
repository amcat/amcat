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
from amcat.models import Task
from amcat.tools import amcattest
from api.rest.serializer import AmCATModelSerializer

__all__ = ("TaskSerializer", "TaskResultSerializer")

class TaskSerializer(AmCATModelSerializer):
    """Represents a Task object defined in amcat.models.task.Task. Adds two
    fields to the model: status and ready."""
    status = serializers.SerializerMethodField('get_status')
    ready = serializers.SerializerMethodField('get_ready')

    def __init__(self, *args, **kwargs):
        super(TaskSerializer, self).__init__(*args, **kwargs)
        self._tasks = {}

    def set_status_ready(self, task):
        ready = task.get_async_result().ready()
        status = task.get_async_result().status
        self._tasks[task] = (status, ready)

    def get_status_ready(self, task):
        """Returns tuple with (status, ready) => (str, bool)"""
        if task not in self._tasks:
            self.set_status_ready(task)
        return self._tasks[task]

    def get_status(self, task):
        status, _ = self.get_status_ready(task)
        return status

    def get_ready(self, task):
        _, ready = self.get_status_ready(task)
        return ready

    class Meta:
        model = Task


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

class TestTaskSerializer(amcattest.AmCATTestCase):
    def test_order(self):
        class MockTask:
            def __init__(self, ready=False, status="PENDING"):
                self._ready = ready
                self._status = status

            def ready(self):
                return self._ready

            @property
            def status(self):
                return self._status

            def get_async_result(self):
                return self

        ts = TaskSerializer()
        mt = MockTask()
        mt2 = MockTask(ready=True, status="SUCCESS")
        mt3 = MockTask()

        # Test simple getting / caching
        self.assertEqual("PENDING", ts.get_status(mt))
        self.assertEqual(False, ts.get_ready(mt))
        self.assertEqual("SUCCESS", ts.get_status(mt2))
        self.assertEqual(True, ts.get_ready(mt2))

        # Test order of ready/status
        self.assertEqual("PENDING", ts.get_status(mt3))
        mt3._ready = True
        self.assertEqual(False, ts.get_ready(mt))


