from cachable import *
import project
import user

class System(Cachable):
    __metaclass__ = CachingMeta
    __table__ = None
    __idcolumn__ = None

    projects = DBFKPropertyFactory("projects", "projectid", dbfunc=project.Project)
    users = DBFKPropertyFactory("users", "userid", dbfunc=user.User)

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
    
    

