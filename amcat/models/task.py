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


import datetime

from django.contrib.auth.models import User
from celery.result import AsyncResult
from jsonfield import JSONField
from django.db import models
from amcat.models import Project
from amcat.tools import classtools
from amcat.tools.caching import cached
from amcat.tools.model import AmcatModel, PostgresNativeUUIDField
from amcat.amcatcelery import app
from amcat.tools.usage import log_usage


IN_PROGRESS = "INPROGRESS"
FAILED = "FAILURE"


@app.task(bind=True)
def amcat_task(self):
    t = Task.objects.get(uuid=self.request.id)
    handler = t.get_handler()
    return handler.run_task()


class TaskPending(Exception):
    pass


class Task(AmcatModel):
    """
    A Task represents a Script (see: amcat.scripts.Script) which was ran asynchronously
    using Celery. Because Celery fails to remember task-names when submitted, they are
    stored here together with the class which executed the task.

    The 'handler' class should inherit from TaskHandler or provide the same interface.
    """
    uuid = PostgresNativeUUIDField(db_index=True, unique=True)
    handler_class_name = models.TextField(null=False, blank=False)
    class_name = models.TextField()
    arguments = JSONField()

    project = models.ForeignKey(Project, null=True)
    user = models.ForeignKey(User, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    # A Task is persistent if it important to keep it around (example: saved queries)
    persistent = models.BooleanField(default=False)

    def _get_raw_result(self):
        """
        Get the 'raw' result of this task.
        Will raise a TaskPending if the task is still pending, and will re-raise
        the original error if the task failed.
        """
        r = self.get_async_result()
        if not r.ready():
            raise TaskPending()
        if r.failed():
            raise r.result
        return r.result

    @cached
    def get_async_result(self):
        """Returns Celery AsyncResult object belonging to this Task."""
        return AsyncResult(id=str(self.uuid), task_name=amcat_task.name, app=app)

    def get_class(self):
        return classtools.import_attribute(self.class_name)

    def get_handler(self):
        return classtools.import_attribute(self.handler_class_name)(self)

    def get_arguments(self):
        """Returns `arguments` deserialised by handler."""
        return self.get_handler().deserialise_arguments(self.arguments)

    def revoke(self, **kwargs):
        """Revoke a task by preventing it from running on workers.

        @type terminate: boolean
        @param terminate: kill currently running task (Celery documentation advises againt using this)
        @type signal: str
        @param signal: signal to send to running process (used in combination with terminate). Default: SIGKILL"""
        return self.get_async_result().revoke(**kwargs)

    @property
    def ready(self):
        return self.get_async_result().ready()


    def log_usage(self, type, action, **extra):
        duration = datetime.datetime.now() - self.issued_at
        extra.update({
            "class": self.class_name,
            "task_handler": self.handler_class_name,
            "task_issued": self.issued_at,
            "task_duration": duration.total_seconds()
        })
        
        log_usage(self.user.username, type, action, self.project, **extra)

        
    class Meta:
        db_table = "tasks"
        app_label = "amcat"


class TaskHandler(object):
    """
    Handler for tasks. run_task is called in a celery thread,
    the get_* methods can be called later to interpret the results
    """

    def __init__(self, task):
        self.task = task

    @classmethod
    def call(cls, target_class, arguments, user, project=None):
        """
        Create a new task object and start it using this class as handler
        @return: an handler object instantiated with the created task
        """
        if not isinstance(target_class, str):
            target_class = classtools.get_qualified_name(target_class)

        if user.is_anonymous():
            user = None
            
        task = Task.objects.create(
            handler_class_name=classtools.get_qualified_name(cls),
            class_name=target_class, user=user, project=project,
            arguments=cls.serialise_arguments(arguments)
        )

        amcat_task.apply_async(task_id=str(task.uuid))
        return cls(task)

    def run_task(self):
        """
        Run the task and return the (json serializable) results
        """
        raise NotImplementedError()

    def get_redirect(self):
        """
        Return a (url, name) pair for redirection after completion
        raises TaskPending if task is not complete yet.
        """
        raise NotImplementedError()

    def get_result(self):
        """
        Return the raw result.
        raises TaskPending if task is not complete yet.
        """
        return self.task._get_raw_result()

    def get_response(self):
        """
        Return a suitable HTTP Response for viewing
        raises TaskPending if task is not complete yet.
        """
        raise NotImplementedError()

    @classmethod
    def serialise_arguments(cls, arguments):
        """Returns object suitable for serialisation by json.dumps()."""
        return arguments.copy()

    @classmethod
    def deserialise_arguments(cls, arguments):
        """Inverse of `serialise_arguments`."""
        return arguments.copy()

