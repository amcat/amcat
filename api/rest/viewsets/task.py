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
import functools
from rest_framework import serializers
from amcat.models.task import IN_PROGRESS, FAILED
from amcat.models import Task
from amcat.tools import amcattest
from api.rest.serializer import AmCATModelSerializer

__all__ = ("TaskSerializer", "TaskResultSerializer")

class TaskSerializer(AmCATModelSerializer):
    """Represents a Task object defined in amcat.models.task.Task. Adds two
    fields to the model: status and ready."""
    description = serializers.SerializerMethodField('get_description')
    status = serializers.SerializerMethodField('get_status')
    ready = serializers.SerializerMethodField('get_ready')
    progress = serializers.SerializerMethodField('get_progress')
    redirect_url = serializers.SerializerMethodField('get_redirect_url')
    redirect_message = serializers.SerializerMethodField('get_redirect_message')

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

    class Meta:
        model = Task


class TaskResultSerializer(AmCATModelSerializer):
    result = serializers.SerializerMethodField('get_result')
    ready = serializers.SerializerMethodField('get_ready')

    def get_ready(self, task):
        return task.ready

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
            def __init__(self, ready=False, status="PENDING", result=None, callback=None):
                self._ready = ready
                self._status = status
                self._result = result
                self.callback = callback

            def ready(self):
                if self.callback: self.callback("_ready")
                return self._ready

            @property
            def status(self, **kwargs):
                if self.callback: self.callback("_status")
                return self._status

            @property
            def result(self):
                if self.callback: self.callback("_result")
                return self._result

            def get_async_result(self):
                return self

        ts = TaskSerializer()
        mt = MockTask()
        mt2 = MockTask(ready=True, status="SUCCESS")
        mt3 = MockTask()
        mt4 = MockTask()

        # Test simple getting / caching
        self.assertEqual("PENDING", ts.get_status(mt))
        self.assertEqual(False, ts.get_ready(mt))
        self.assertEqual("SUCCESS", ts.get_status(mt2))
        self.assertEqual(True, ts.get_ready(mt2))

        # Test order of ready/status/result
        def _change(task, set_prop, set_value, prop, callprop):
            if prop == callprop:
                setattr(task, set_prop, set_value)

        # Set ready to True when _result is fetched
        change = functools.partial(_change, mt3, "_ready", True, "_result")
        mt3.callback = change

        self.assertEqual("PENDING", ts.get_status(mt3))
        self.assertEqual(False, ts.get_ready(mt3))
        self.assertEqual(True, mt3._ready)

        # Set ready to True when _status is fetched
        change = functools.partial(_change, mt4, "_ready", True, "_status")
        mt4.callback = change

        self.assertEqual("PENDING", ts.get_status(mt4))
        self.assertEqual(False, ts.get_ready(mt4))
        self.assertEqual(True, mt4._ready)
