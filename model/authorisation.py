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

from django.db import models

ADMIN_ROLE = 1

class AccessDenied(EnvironmentError):
    def __init__(self, user, privilege, project=None):
        roles = getRoles(user)
        projectstr = " on %s" % project if project else ""
        msg = "Access denied for privilege %s%s to %s\nRequired role %s, has roles %s" % (
            privilege.label, projectstr, user.label, privilege.role.label, [r.label for r in roles])
        EnvironmentError.__init__(self, msg)

def check(db_or_user, privilege, onproject=None):
    """Check whether the logged-in user is authorised 

    If permission is denied, will raise L{AccessDenied}; otherwise will
    return silently
    
    @param db_or_user: db connection with the user to check logged in, or the
      user object to check
    @type privilege: Privilege object, id, or str
    @param privilege: The requested privilege
    @param onproject: The project the privilege is requested on,
      or None (ignored) for global privileges
    @return: None (raises exception if denied)
    """
    if hasattr(db_or_user, 'getUser'):
        db, checkuser = db_or_user, db_or_user.getUser()
    else:
        db, checkuser = db_or_user.db, db_or_user
    
    userroles =getRoles(checkuser)

    p = getPrivilege(db, privilege)
    neededroleid = p.role.id    
    if p.projectlevel:
        if onproject is None:
            raise ValueError("Cannot check project privilege %s without project" % (p))
        if type(onproject) == int:
            from amcat.model import project
            onproject = project.Project(db, onproject)
        # global admin can do anything on any project:
        if any(r.id == ADMIN_ROLE for r in userroles): return
        projectroles = getRoles(checkuser, onproject)
        if not any(r.id in (ADMIN_ROLE, neededroleid) for r in projectroles):
            raise AccessDenied(checkuser, p, onproject)
    else:
        if not any(r.id in (ADMIN_ROLE, neededroleid) for r in userroles):
            raise AccessDenied(checkuser, p)

def getPrivilege(db, privilege):
    """Find a privilege object by name or number

    Raises an exception if the privilege cannot be found
    
    @param db: a database connection
    @type privilege: int, str, or L{Privilege}
    @param privilege: the privelege to be found
    @return: L{privilege}
    """
    if isinstance(privilege, Privilege):
        return privilege
    for p in Privilege.all(db):
        if privilege in (p.id, p.label):
            return p
    raise ValueError("Privilege %r cannot be found" % privilege)

def getRoles(user, onproject=None):
    """Get all roles for the user (on the project)"""
    if onproject is None:
        return user.roles
    return user.projectroles.get(onproject, [])

class Role(models.Model):
    id = models.IntegerField(primary_key=True, db_column='role_id')
    label = models.CharField(max_length=50)

    def __unicode__(self):
        return self.label

    class Meta():
        db_table = 'roles'
        app_label = 'models'

class ProjectRole(models.Model):
    project = models.ForeignKey("models.Project")
    user = models.ForeignKey("models.User")
    role = models.ForeignKey(Role)

    def __unicode__(self):
        return u"%s, %s" % (self.project, self.role)

    class Meta():
        db_table = 'projects_users_roles'
        unique_together = ("project", "user", "role")
        app_label = 'models'

class Privilege(models.Model):
    id = models.IntegerField(primary_key=True, db_column='privilege_id')

    label = models.CharField(max_length=50)
    projectlevel = models.BooleanField()
    role = models.ForeignKey(Role)

    def __unicode__(self):
        return self.label

    class Meta():
        db_table = 'privileges'
        app_label = 'models'