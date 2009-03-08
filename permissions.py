
class PermissionLevel(object):
    def __init__(self, id, name, fullName):
        self.id = id
        self.name = name
        self.fullName = fullName

CODER = 1#PermissionLevel(1, 'coder', 'Coder')
USER = 2
ADMIN = 3
SUPER_ADMIN = 4

HIDDEN_VISIBILITY = 1
META_VISIBILITY = 2
FULL_VISIBILITY = 3

PROJECT_CODER = 1
PROJECT_READ = 2
PROJECT_READ_WRITE = 3
PROJECT_ADMIN = 4

VISIBILITY = ((HIDDEN_VISIBILITY, 'hidden'), (META_VISIBILITY, 'metadata visible'), (FULL_VISIBILITY, 'full visibility'))
USER_PERMISSION = ((CODER, 'coder'), (USER, 'normal user'), (ADMIN, 'admin'), (SUPER_ADMIN, 'super admin'))







def projectVisibility(db, projectid):
    data = db.doQuery("""
        SELECT TOP 1 visibility FROM project_visibility
        WHERE projectid = %d""" % projectid)
    return data[0][0]
    
    
def userPermission(db, userid):
    data = db.doQuery("""
        SELECT TOP 1 permissionid FROM permissions_users WHERE userid = %d""" % userid)
    return data[0][0]
    
    
def projectUserPermission(db, projectid, userid):
    data = db.doQuery("""
        SELECT TOP 1 permissionid FROM permissions_projects_users WHERE userid = %d AND projectid = %d""" % (userid, projectid))
    return data[0][0] if data else None
    
    
    