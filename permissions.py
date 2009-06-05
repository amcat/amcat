from enum import Enum, EnumValue

UserPermission = Enum(
    EnumValue("CODER", "Coder", 1),
    EnumValue("USER", "Normal User", 2),
    EnumValue("ADMIN", "Admin", 3),
    EnumValue("SUPER_ADMIN", "Super Admin", 4),
)

ProjectVisibility = Enum(
    EnumValue("HIDDEN", "Hidden", 1),
    EnumValue("META", "Metadata Visible", 2),
    EnumValue("FULL", "Fully visible", 3),
)

ProjectPermission = Enum(
    EnumValue("CODER", "Coder", 1),
    EnumValue("READ", "Read only", 2),
    EnumValue("READ_WRITE", "Read/Write", 3),
    EnumValue("ADMIN", "Admin", 4),

)

# def projectVisibility(db, projectid):
#     data = db.doQuery("""
#         SELECT TOP 1 visibility FROM project_visibility
#         WHERE projectid = %d""" % projectid)
#     return data[0][0]
    
    
# def userPermission(db, userid):
#     data = db.doQuery("""
#         SELECT TOP 1 permissionid FROM permissions_users WHERE userid = %d""" % userid)
#     return data[0][0]
    
    
# def projectUserPermission(db, projectid, userid):
#     data = db.doQuery("""
#         SELECT TOP 1 permissionid FROM permissions_projects_users WHERE userid = %d AND projectid = %d""" % (userid, projectid))
#     return data[0][0] if data else None
    
    
if __name__ == '__main__':
    print ProjectPermission.CODER.label
    print ProjectVisibility.get(3).name
