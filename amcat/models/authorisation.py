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
from enum import Enum
from typing import Union

from django.contrib.auth.models import User

from django.db import models
from amcat.tools.model import AmcatModel
from django.core.exceptions import PermissionDenied



class PROJECT_ROLES(Enum):
    METAREADER = 10
    READER = 11
    WRITER = 12
    ADMIN = 13

# todo: replace usages with the PROJECT_ROLES enum members.
ROLE_PROJECT_METAREADER = PROJECT_ROLES.METAREADER.value
ROLE_PROJECT_READER = PROJECT_ROLES.READER.value
ROLE_PROJECT_WRITER = PROJECT_ROLES.WRITER.value
ROLE_PROJECT_ADMIN = PROJECT_ROLES.ADMIN.value

class AccessDenied(PermissionDenied):
    def __init__(self, user, privilege, project=None):
        projectstr = " on %s" % project if project else ""
        msg = "Access denied for privilege %s%s to %s\nRequired role %s, has role %s" % (
            privilege, projectstr, user, privilege.role, user.userprofile.role)
        super().__init__(self, msg)


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
