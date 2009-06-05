from cachable import Cachable
import toolkit, permissions, project

_users = None
def users(db):
    global _users
    if _users is None:
        _users = Users(db)
    return _users
        
class Users(object):
    def __init__(self, db):
        self.db = db
        self.byid, self.byname = {}, {}
        SQL = "select userid, username from users"
        for uid, username in db.doQuery(SQL):
            u = User(db, uid, username=username)
            self.byid[uid] = u
            self.byname[u.username] = u
    def getUser(self, userid):
        return self.byid[userid]
    def getByName(self, username):
        return self.byname[username]

class User(Cachable):
    __table__ = 'users'
    __idcolumn__ = 'userid'
    def __init__(self, db, id, username=None):
        Cachable.__init__(self, db, id)
        for prop in "username", "fullname", "affiliation", "active", "email":
            self.addDBProperty(prop)
        self.addDBProperty("permissionLevel", "permissionid", table="permissions_users", func=permissions.UserPermission.get)
        if username is not None:
            self.cacheValues(username=username)

    def __str__(self):
        return self.username
    
    def idname(self):
        return "%i - %s" % (self.id, self.username)

    @property
    def permissionLevelName(self):
        return self.permissionLevel.label
    
    def projects(self, own):
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
        
        
    
        
        
