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
from amcat.tools.model import AmcatModel

ADMIN_ROLE = 1

class AccessDenied(EnvironmentError):
    def __init__(self, user, privilege, project=None):
        roles = user.roles.all()
        projectstr = " on %s" % project if project else ""
        msg = "Access denied for privilege %s%s to %s\nRequired role %s, has roles %s" % (
            privilege, projectstr, user, privilege.role, [r for r in roles])
        EnvironmentError.__init__(self, msg)

def check(user, privilege, project=None):
    """Check `user` for `privilege`.

    If permission is denied, will raise L{AccessDenied}; otherwise will
    return silently
    
    @type user: user.User
    @param user: User to check for `privilege`

    @type privilege: Privilege object, id, or str
    @param privilege: The requested privilege

    @param project: The project the privilege is requested on,
      or None (ignored) for global privileges

    @return: None (raises exception if denied)
    """
    def get_priv(priv, prjct):
        if isinstance(priv, models.Model):
            return priv
        elif isinstance(priv, basestring):
            return Privilege.objects.get(label=priv, projectlevel=bool(prjct))
        return Privilege.objects.get(id=priv)

    roles = user.get_roles()
    priv = get_priv(privilege, project)
    nrole = priv.role # Needed role

    if priv.projectlevel:
        if project is None:
            raise("Cannot check project privilege %s without project" % priv)
        
        if any(r.id == ADMIN_ROLE for r in roles):
            # User is admin
            return
        
        # userroles --> projectroles
        roles = user.get_roles(project)
        
    if not any(r.id in (ADMIN_ROLE, nrole.id) for r in roles):
        raise AccessDenied(user, priv, project)


class Role(AmcatModel):
    id = models.IntegerField(primary_key=True, db_column='role_id')
    label = models.CharField(max_length=50)

    def __unicode__(self):
        return self.label

    class Meta():
        db_table = 'roles'

class ProjectRole(AmcatModel):
    project = models.ForeignKey("model.Project")
    user = models.ForeignKey("model.User")
    role = models.ForeignKey(Role)

    def __unicode__(self):
        return u"%s, %s" % (self.project, self.role)

    class Meta():
        db_table = 'projects_users_roles'
        unique_together = ("project", "user", "role")

class Privilege(AmcatModel):
    id = models.IntegerField(primary_key=True, db_column='privilege_id')

    label = models.CharField(max_length=50)
    projectlevel = models.BooleanField()
    role = models.ForeignKey(Role)

    def __unicode__(self):
        return self.label

    class Meta():
        db_table = 'privileges'