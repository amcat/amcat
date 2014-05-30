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


from amcat.scripts.script import Script
from amcat.tools import amcattest
from amcat.models import Task, TaskHandler
from celery.task import task
from api.webscripts.webscript import WebScript


class _TestTaskScript(Script):
    pass

class _TestHandler(TaskHandler):
    pass

class _TestTaskWebScript(WebScript):
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        super(_TestTaskWebScript, self).__init__(*args, **kwargs)

    @classmethod
    def get_called_with(cls, **called_with):
        called_with["test"] += 1
        return called_with

#TODO: Test handler operations
class TestTask(amcattest.AmCATTestCase):
    def _get_task(self):
        return task(lambda : None).delay()

    def test_get_async_result(self):
        user = amcattest.create_test_user()

        task = self._get_task()
        task_model = Task.objects.create(uuid=task.id, class_name=":)", user=user)
        self.assertEqual(task.id, task_model.get_async_result().id)

    def test_get_class(self):
        user = amcattest.create_test_user()
        task = Task.objects.create(class_name="amcat.tests.test_task._TestTaskScript", user=user)
        self.assertEqual(_TestTaskScript.__name__, task.get_class().__name__)

    def test_get_handler(self):
        user = amcattest.create_test_user()
        task = Task.objects.create(
            class_name="amcat.tests.test_task._TestTaskWebScript",
            handler_class_name="amcat.tests.test_task._TestHandler",
            user=user)

        self.assertEqual(task.get_handler().__class__, _TestHandler)
