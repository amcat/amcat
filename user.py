from cachable2 import Cachable, DBProperty, ForeignKey, DBProperties
import toolkit, permissions, project, authorisation, language

def getProjectRole(db, projectid, roleid):
    return project.Project(db, projectid), authorisation.Role(db, roleid)

class User(Cachable):
    __table__ = 'users'
    __idcolumn__ = 'userid'
    __labelprop__ = 'username'

    permissionLevel = DBProperty(table="permissions_users", getcolumn="permissionid", deprecated=True)
    
    userid, username, fullname, affiliation, active, email = DBProperties(6)
    language = DBProperty(lambda : language.Language)
    roles = ForeignKey(lambda : authorisation.Role, table="users_roles")
    projects = ForeignKey(lambda : project.Project, table="permissions_projects_users")
    projectroles = ForeignKey(lambda : (project.Project, authorisation.Role),
                              table="projects_users_roles", sequencetype=toolkit.multidict)
    
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
        
if __name__ == '__main__':
    import dbtoolkit
    print User.projects.getType()
    print User.projects.getCardinality()
    print dbtoolkit.amcatDB().getUser().projects
    print list(dbtoolkit.amcatDB().getUser().projects)
    

