from __future__ import unicode_literals, print_function, absolute_import
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

from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.tools import toolkit
from amcat.model import permissions, project, authorisation, language

def getProjectRole(db, projectid, roleid):
    return project.Project(db, projectid), authorisation.Role(db, roleid)

class Affiliation(Cachable):
    __table__ = 'affiliations'
    __idcolumn__ = 'affiliationid'
    __labelprop__ = 'name'
    
    name = DBProperty()
    users = ForeignKey(lambda : User)
    
class User(Cachable):
    __table__ = 'users'
    __idcolumn__ = 'userid'
    __labelprop__ = 'username'

    permissionLevel = DBProperty(table="permissions_users", getcolumn="permissionid", deprecated=True)
    
    userid, username, fullname, affiliationid, active, email, languageid = DBProperties(7)
    language = DBProperty(lambda : language.Language)
    roles = ForeignKey(lambda : authorisation.Role, table="users_roles")
    projects = ForeignKey(lambda : project.Project, table="projects_users_roles")
    projectroles = ForeignKey(lambda : (project.Project, authorisation.Role),
                              table="projects_users_roles", sequencetype=toolkit.multidict)
    
    affiliation = DBProperty(lambda : Affiliation, getcolumn="affiliationid")
    
    @classmethod
    def create(cls, db, **props):
        
        
        super(User, cls).create(db, **props)
    
    def haspriv(self, privilege, onproject=None):
        """If permission is denied, this function returns False,
        if permission granted it returns True.
        
        @type privilege: Privilege object, id, or str
        @param privilege: The requested privilege
        @param onproject: The project the privilege is requested on,
          or None (ignored) for global privileges
        
        @return: True or False (see above)"""
        try: authorisation.check(self, privilege, onproject)
        except authorisation.AccessDenied:
            return False
        
        return True
    
    @classmethod
    def create(cls, db, idvalues=None, **props):
                
        super(User, cls).create(db, idvalues=None, **props)
        
    @property
    @toolkit.deprecated
    def canCreateNewProject(self): return False
    
    @property
    @toolkit.deprecated
    def canViewAllProjects(self): return self.permissionLevel > 2

    @property
    @toolkit.deprecated
    def canViewAffiliationUserList(self): return True
        
    @property
    @toolkit.deprecated
    def canViewUserList(self): return True

    @property
    @toolkit.deprecated
    def canAddNewUserToAffiliation(self): return False
    
    @property
    @toolkit.deprecated
    def isSuperAdmin(self): return self.permissionLevel >= 4

    
@toolkit.deprecated
def currentUser(db):
    return db.getUser()
        
@toolkit.deprecated
def users(db):
    import system
    return system.System(db).users
        
