from toolkit import cached
import toolkit, permissions, project


def users(db, projectid=None, affiliation=None):
    users = Users(db, projectid, affiliation)
    for id, u in sorted(users.byid.items()):
        yield u

        
class Users(object):
    def __init__(self, db, projectid=None, affiliation=None):
        self.db = db
        self.byid, self.byname = {}, {}
        SQL = "select u.username, u.userid from users AS u"
        if projectid:
            SQL += ' WHERE exists (SELECT ppu.userid FROM permissions_projects_users AS ppu WHERE u.userid = ppu.userid AND ppu.projectid = %d)' % projectid
        elif affiliation:
            SQL += ' WHERE u.affiliation = %s' % db.quote(affiliation)
        for un, uid in db.doQuery(SQL):
            u = User(db, uid, un)
            self.byid[uid] = u
            self.byname[un] = u
    
    def getUser(self, userid):
        return self.byid[userid]
    
    def getByName(self, username):
        return self.byname[username]


class User(object):
    def __init__(self, db, id, username = None, permissionLevel = None):
        self.db = db
        self.id = id
        self._username = username
        self._permissionLevel = permissionLevel

        
    def _getFields(self):
        if self._field: return
        SQL = "select username, fullname, affiliation, active, email FROM users WHERE userid = %i" % self.id
        self._username, self._fullname, self._affiliation, self._active, self._email = self.db.doQuery(SQL)[0]
        self._field = True
    _field = False
        
    @property
    #@cached
    def username(self):
        if not self._username:
            self._getFields()
        return self._username
    
    def idname(self):
        return "%i - %s" % (self.id, self.username)

    @property
    #@cached
    def fullname(self):
        self._getFields()
        return self._fullname

    @property
    #@cached
    def affiliation(self):
        self._getFields()
        return self._affiliation

    @property
    #@cached
    def email(self):
        self._getFields()
        return self._email

    @property
    #@cached
    def active(self):
        self._getFields()
        return self._active

    
    def projects(self, own):
        return project.projects(self.db, self.id, own=own)
        
    @property
    def canCreateNewProject(self):
        level = permissions.userPermission(self.db, self.id)
        if level == permissions.CODER:
            return False
        return True
    
    @property
    def canViewAllProjects(self):
        level = permissions.userPermission(self.db, self.id)
        if level == permissions.CODER:
            return False
        return True
    
    @property
    def canViewAffiliationUserList(self):
        level = permissions.userPermission(self.db, self.id)
        if level == permissions.CODER:
            return False
        return True
        
    @property
    def canViewUserList(self):
        level = permissions.userPermission(self.db, self.id)
        if level != permissions.SUPER_ADMIN:
            return False
        return True 
    
    @property
    def canAddNewUserToAffiliation(self):
        level = permissions.userPermission(self.db, self.id)
        if level == permissions.SUPER_ADMIN or level == permissions.ADMIN:
            return True
        return False
    
    @property
    def isSuperAdmin(self):
        level = permissions.userPermission(self.db, self.id)
        if level == permissions.SUPER_ADMIN:
            return True
        return False
        
        
    @property
    def permissionLevel(self):
        level = permissions.userPermission(self.db, self.id)
        for l, name in permissions.USER_PERMISSION:
            if l == level: return name
        raise Exception('permission level not found for %s' % self.id)
        
        