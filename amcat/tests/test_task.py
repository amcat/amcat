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

"""
A Job
"""
from amcat.scripts.script import Script
from amcat.tools import amcattest
from amcat.models import Task
from celery.task import task


class _TestTaskScript(Script):
    pass


class TestTask(amcattest.AmCATTestCase):
    def _get_task(self):
        return task(lambda : None).delay()

    def test_get_result(self):
        user = amcattest.create_test_user()

        task = self._get_task()
        task_model = Task.objects.create(uuid=task.id, task_name=task.task_name, class_name=":)", user=user)
        self.assertEqual(task.id, task_model.uuid)
        self.assertEqual(task.id, task_model.get_async_result().id)
        self.assertEqual(task.task_name, task_model.get_async_result().task_name)
        self.assertEqual(task, task_model.get_async_result())

    def test_get_class(self):
        user = amcattest.create_test_user()
        task = Task.objects.create(uuid="bar", task_name="foo", class_name="amcat.tests.test_task._TestTaskScript", user=user)
        self.assertEqual(_TestTaskScript.__name__, task.get_class().__name__)

