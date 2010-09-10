from cachable import *
import project, user

from annotationschema import AnnotationSchema, AnnotationSchemaFieldtype

class System(Cachable):
    __metaclass__ = CachingMeta
    __table__ = None
    __idcolumn__ = None

    projects = DBFKPropertyFactory("projects", "projectid", dbfunc=project.Project)
    users = DBFKPropertyFactory("users", "userid", dbfunc=user.User)
    annotationschemas = DBFKPropertyFactory("annotationschemas", "annotationschemaid", dbfunc=AnnotationSchema)
    fieldtypes = DBFKPropertyFactory("annotationschemas_fieldtypes", "fieldtypeid", dbfunc=AnnotationSchemaFieldtype)
    
    @property
    def schematypes(self):
        # Seems to be hardcoded (i.e. not stored in table)
        res = []
        for (i, label) in enumerate(('Net', 'Simple')):
            res.append(Schematype(i, label))
        return res
    
    def getUserByUsername(self, uname):
        cacheMultiple(self.users, ["username",])
        
        for usr in self.users:
            if usr.username == uname:
                return usr

        
class Schematype(object):
    def __init__(self, id, label):
        self.id = id
        self.label = label

if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True)
    print "Querying System object"
    system = System(db, ())
    print system.projects
    u = list(system.users)
    db.printProfile()

    print "Querying second system object"
    system2 = System(db, ())
    s = system.projects
    u = system.users
    db.printProfile()