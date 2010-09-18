from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory, CachingMeta
import toolkit, permissions, project

_users = None
def users(db):
    """Access singleton Users object"""
    global _users
    if _users is None:
        _users = Users(db)
    return _users
        
class Users(object):
    def __init__(self, db):
        self.db = db
        self.byid, self.byname = {}, {}
        SQL = "select userid from users"
        for uid, in db.doQuery(SQL):
            u = User(db, uid)
            self.byid[uid] = u
            self.byname[u.username] = u
    def getUser(self, userid):
        return self.byid[userid]
    def getByName(self, username):
        return self.byname[username]
    def __iter__(self):
        for user in self.byid.values():
            yield user
            
def addUser(db, uname, passwd, fullname, affiliation, email, permissionLevel):
    """Add a user to the system. Return new UID."""
    
    sql = "exec newcoder '%s', '%s', '%s', '%s', '%s', '%s'"
    args = (uname, passwd, fullname, email, affiliation, permissionLevel)
    
    db.commit()
    uid = db.doSafeQuery(sql, *args)
    db.commit()
    
    return uid

class User(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'users'
    __idcolumn__ = 'userid'
    __labelprop__ = 'username'
    

    __dbproperties__ = ["username", "fullname", "affiliation", "active", "email", "language"]
    permissionLevel = DBPropertyFactory("permissionid", table="permissions_users", func=permissions.UserPermission.get)
    projects = DBFKPropertyFactory("permissions_projects_users", "projectid", dbfunc=lambda db, id : project.Project(db, id))

    def permissionLevel_update(self, value):
        p = Permission(self.db, self.id)
        p.update(permissionid=value)
    
    @property
    def permissionLevelName(self):
        if self.permissionLevel is None:
            return "None"
        else:
            return self.permissionLevel.label
    
    def getProjects(self, own):
        return project.projects(self.db, self.id, own=own)
        
    @property
    def canCreateNewProject(self):
        return self.permissionLevel.value > permissions.UserPermission.CODER.value
    
    @property
    def canViewAllProjects(self):
        return self.permissionLevel.value > permissions.UserPermission.CODER.value
    
    @property
    def canViewAffiliationUserList(self):
        return self.permissionLevel.value > permissions.UserPermission.CODER.value
        
    @property
    def canViewUserList(self):
        return self.permissionLevel.value >= permissions.UserPermission.SUPER_ADMIN.value

    @property
    def canAddNewUserToAffiliation(self):
        return self.permissionLevel.value >= permissions.UserPermission.ADMIN.value
    
    @property
    def isSuperAdmin(self):
        return self.permissionLevel.value >= permissions.UserPermission.SUPER_ADMIN.value
    


class Permission(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'permissions_users'
    __idcolumn__ = 'userid'
    __labelprop__ = 'userid'
    
    __dbproperties__ = ["permissionid"]
        
def currentUser(db):
    uid = db.getValue("select dbo.anoko_user()")
    return User(db, uid)
    
        
        
if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB()
    print currentUser(db)

