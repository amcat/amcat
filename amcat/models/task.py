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
This module contains logic concerning tasks, which are Celery jobs created
by a Script object.
"""

from __future__ import unicode_literals, print_function, absolute_import
from django.contrib.auth.models import User
from celery.result import AsyncResult

from django.db import models
from amcat.models import Project
from amcat.tools import classtools
from amcat.tools.model import AmcatModel
from amcat.forms.fields import JSONField

class Task(AmcatModel):
    """
    A Task represents a Script (see: amcat.scripts.Script) which was ran asynchronously
    using Celery. Because Celery fails to remember task-names when submitted, they are
    stored here together with the class which executed the task.
    """
    uuid = models.CharField(max_length=36, db_index=True)
    task_name = models.TextField()
    class_name = models.TextField()
    issued_at = models.DateTimeField(auto_now_add=True)
    called_with = JSONField()

    project = models.ForeignKey(Project, null=True)
    user = models.ForeignKey(User, null=False)

    # A Task is persistent if it important to keep it around (example: saved queries)
    persistent = models.BooleanField(default=False)

    def _assert_ready(self):
        assert(self.get_async_result().ready())

    def get_async_result(self):
        """Returns Celery AsyncResult object belonging to this Task."""
        return AsyncResult(id=self.uuid, task_name=self.task_name)

    def get_result(self):
        """Get """
        self._assert_ready()
        return self.get_object().get_result(self.get_async_result().result)

    def get_response(self):
        self._assert_ready()
        return self.get_object().get_response(self.get_async_result().result)

    def get_class(self):
        return classtools.import_attribute(self.class_name)

    def get_object(self):
        """Instantiate `class_name` with original arguments."""
        return self.get_class()(**self.called_with)

    def revoke(self, **kwargs):
        """Revoke a task by preventing it from running on workers.

        @type terminate: boolean
        @param terminate: kill currently running task (Celery documentation advises againt using this)
        @type signal: basestring
        @param signal: signal to send to running process (used in combination with terminate). Default: SIGKILL"""
        return self.get_async_result().revoke(**kwargs)


    class Meta:
        db_table = "tasks"
        app_label = "amcat"


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
# See: amcat.tests.test_task
