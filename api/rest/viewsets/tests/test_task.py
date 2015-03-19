import functools
from amcat.tools import amcattest
from api.rest.viewsets import TaskSerializer


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