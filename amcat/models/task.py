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

from __future__ import unicode_literals, print_function, absolute_import
from celery.task import task
from django.core.urlresolvers import reverse
from celery.result import AsyncResult

from django.db import models
from amcat.models import Project
from amcat.tools import classtools
from amcat.tools.model import AmcatModel

class Task(AmcatModel):
    """
    A Task represents a Script (see: amcat.scripts.Script) which was ran asynchronously
    using Celery. Because Celery fails to remember task-names when submitted, they are
    stored here together with the class which executed the task.
    """
    uuid = models.CharField(max_length=36)
    task_name = models.TextField()
    class_name = models.TextField()
    project = models.ForeignKey(Project, null=True)

    def get_result(self):
        """Returns Celery AsyncResult object belonging to this Task."""
        return AsyncResult(id=self.uuid, task_name=self.task_name)

    def get_class(self):
        return classtools.import_attribute(self.class_name)

    def get_url(self):
        """
        Returns url where result / current progress can be viewed.

        @requires: this.project is not None
        @return: absolute url (string)
        """
        if not self.get_result().ready():
            return reverse('navigator.views.project.job', args=[str(self.project_id), self.uuid])
        return self.get_class().get_url(self.get_result().result, project=self.project)

    class Meta:
        db_table = "tasks"
        app_label = "amcat"


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

# See: amcat.tests.test_task
