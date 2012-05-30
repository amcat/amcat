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

ADMIN_ROLE = 3

class AccessDenied(EnvironmentError):
    def __init__(self, user, privilege, project=None):
        projectstr = " on %s" % project if project else ""
        msg = "Access denied for privilege %s%s to %s\nRequired role %s, has role %s" % (
            privilege, projectstr, user, privilege.role, user.role)
        EnvironmentError.__init__(self, msg)

def check(user, privilege, project=None):
    """Check `user` for `privilege`.

    If permission is denied, will raise L{AccessDenied}; otherwise will
    return silently

    @type user: user.User
    @param user: User to check for `privilege`

    @type privilege: Privilege object or str
    @param privilege: The requested privilege

    @param project: The project the privilege is requested on,
      or None (ignored) for global privileges

    @return: None (raises exception if denied)
    """
    if isinstance(privilege, basestring):
        privilege = Privilege.objects.get(label=privilege, role__projectlevel=bool(project))

    if not user.is_superuser:
        nrole = privilege.role # Needed role

        try:
            role = (Role.objects.get(projectrole__user=user, projectrole__project=project)
                    if privilege.role.projectlevel else user.get_profile().role)
        except Role.DoesNotExist:
            # User has no role on this project!
            raise AccessDenied(user, privilege, project)

        # Return None if access is OK
        if role.id < nrole.id:
            raise AccessDenied(user, privilege, project)

class RoleManager(models.Manager):
    """
    Implements a natural key for Role-objects. This is needed for MySQL, which does not
    support 'forced' values of AutoFields.
    """
    def get_by_natural_key(self, label, projectlevel):
        return self.get(label=label, projectlevel=projectlevel)

class Role(AmcatModel):
    objects = RoleManager()

    id = models.AutoField(primary_key=True, db_column='role_id')
    label = models.CharField(max_length=50)
    projectlevel = models.BooleanField()

    class Meta():
        db_table = 'roles'
        app_label = 'amcat'
        unique_together = ("label", "projectlevel")

class ProjectRole(AmcatModel):
    project = models.ForeignKey("amcat.Project", db_index=True)
    user = models.ForeignKey(User, db_index=True)
    role = models.ForeignKey(Role)

    def __unicode__(self):
        return u"%s, %s" % (self.project, self.role)

    class Meta():
        db_table = 'projects_users_roles'
        unique_together = ("project", "user")
        app_label = 'amcat'

    def can_update(self, user):
        return user.haspriv('manage_project_users', self.project)

    def can_delete(self, user):
        return user.haspriv('manage_project_users', self.project)

class Privilege(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='privilege_id')

    label = models.CharField(max_length=50)
    role = models.ForeignKey(Role)

    class Meta():
        db_table = 'privileges'
        app_label = 'amcat'
