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

getPrivilege(db, str or int) returns Privilege object
check(db, privilege/str/int) checks whether user has privilege
"""

import system
from cachable import Cachable, DBPropertyFactory
from project import Project

class AccessDenied(EnvironmentError):
    def __init__(self, user, privilege, roles):
        msg = "Access denied for privilege %s to %s\nRequired role %s, has roles %s" % (
            privilege.label, user.label, privilege.role.label, [r.label for r in roles])
        EnvironmentError.__init__(self, msg)

def check(db, privilege, project=None):
    """Check whether the logged-in user is authorised 

    If permission is denied, will raise L{AccessDenied}; otherwise will
    return silently
    
    @param db: db connection with the 'current user' logged in
    @type privilege: Privilege object, id, or str
    @param privilege: The requested privilege
    @param project: The project the privilege is requested on,
      or None (ignored) for global privileges
    @return: None (raises exception if denied)
    """
    p = getPrivilege(db, privilege)
    if p.projectlevel:
        project = None
    elif type(project) == int:
        project = Project(db, project)
    if project:
        #TODO implement role getting for projects!
        return 
    neededroleid = p.role.id
    roles = getRoles(db.getUser(), project)
    for r in roles:
        if r.id == 1: return # admin can do what he wants
        if r.id == neededroleid: return
    raise AccessDenied(db.getUser(), p, roles)

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
    for p in system.System(db).privileges:
        if privilege in (p.id, p.label):
            return p
    raise ValueError("Privilege %r cannot be found" % privilege)

def getRoles(user, project=None):
    """Get all roles for the user (on the project)"""
    if project is None:
        return user.roles
    
class Role(Cachable):
    __table__ = 'roles'
    __idcolumn__ = 'roleid'

    __dbproperties__ = ['label']

class Privilege(Cachable):
    __table__ = 'privileges'
    __idcolumn__ = 'privilegeid'
    __dbproperties__ = ['label', 'projectlevel']
    role = DBPropertyFactory("roleid", dbfunc=Role)

