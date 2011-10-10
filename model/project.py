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

"""ORM Module representing projects"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools import toolkit
from amcat.tools.model import AmcatModel

from django.db import models

class Project(AmcatModel):
    id = models.IntegerField(primary_key=True, db_column='project_id', editable=False)

    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200, null=True)

    insert_date = models.DateTimeField(db_column='insertdate', auto_now_add=True)
    owner = models.ForeignKey("model.User", db_column='owner_id')

    insert_user = models.ForeignKey("model.User", db_column='insertuser_id',
                                    related_name='inserted_project',
                                    editable=False)

    guest_role = models.ForeignKey("model.Role")

    def __unicode__(self):
        return self.name

    def can_read(self, user):
        return (self in user.projects or user.haspriv('view_all_projects'))

    @property
    def users(self):
        return (r.user for r in self.projectrole_set.all())
        
    class Meta():
        db_table = 'projects'

