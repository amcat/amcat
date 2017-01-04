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
Module containing classes and utility functions related to AmCAT authorisation

Main entry points are

check(db, privilege/str/int) checks whether user has privilege
getPrivilege(db, str or int) returns Privilege object

"""
from django.contrib.auth.models import User

from django.db import models
from amcat.tools.model import AmcatModel

ROLE_PROJECT_METAREADER = 10
ROLE_PROJECT_READER = 11
ROLE_PROJECT_WRITER = 12
ROLE_PROJECT_ADMIN = 13


class AccessDenied(EnvironmentError):
    def __init__(self, user, privilege, project=None):
        projectstr = " on %s" % project if project else ""
        msg = "Access denied for privilege %s%s to %s\nRequired role %s, has role %s" % (
            privilege, projectstr, user, privilege.role, user.userprofile.role)
        EnvironmentError.__init__(self, msg)


class Role(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='role_id')
    label = models.CharField(max_length=50, unique=True)

    class Meta():
        db_table = 'roles'
        app_label = 'amcat'


class ProjectRole(AmcatModel):
    project = models.ForeignKey("amcat.Project", db_index=True)
    user = models.ForeignKey(User, db_index=True)
    role = models.ForeignKey(Role)

    def __str__(self):
        return "%s, %s" % (self.project, self.role)

    class Meta():
        db_table = 'projects_users_roles'
        unique_together = ("project", "user")
        app_label = 'amcat'


class Privilege(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='privilege_id')

    label = models.CharField(max_length=50)
    role = models.ForeignKey(Role)

    class Meta():
        db_table = 'privileges'
        app_label = 'amcat'
