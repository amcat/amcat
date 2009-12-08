from cachable import Cachable
import user, permissions, article
from functools import partial

def projects(db, userid, own=1):
    if own:
        sql = """
            SELECT p.projectid
            FROM projects AS p
            INNER JOIN permissions_projects_users as ppu
                ON ppu.projectid = p.projectid
            WHERE ppu.userid = %d
            ORDER BY p.projectid DESC
            """ % userid
    else: # all projects
        sql = """
            SELECT DISTINCT p.projectid
            FROM projects AS p
            LEFT JOIN permissions_projects_users as ppu
                ON ppu.projectid = p.projectid
            INNER JOIN project_visibility AS pv
                ON p.projectid = pv.projectid
            WHERE (ppu.userid = %d OR pv.visibility > 1)
            ORDER BY p.projectid DESC
            """ % userid
    data = db.doQuery(sql, colnames=0)
    for row in data:
        yield Project(db, row[0])


class Project(Cachable):
    __table__ = 'projects'
    __idcolumn__ = 'projectid'
    
    def __init__(self, db, id):
        Cachable.__init__(self, db, id)
        for prop in "name", "insertDate", "description":
            self.addDBProperty(prop)
        self.addDBFKProperty("batches", "batches", "batchid", function=partial(Batch, db, project=self))
        self.addDBProperty("visibility", func=permissions.ProjectVisibility.get, table="project_visibility")
        self.addDBProperty("insertUser", "insertuserid", user.users(self.db).getUser)
        self.addDBFKProperty("users", "permissions_projects_users", "userid", function=user.users(self.db).getUser)

    @property
    def href(self):
        return '<a href="projectDetails?projectid=%i">%i - %s</a>' % (self.id, self.id, self.name)

    def userPermission(self, user):
        p = self.db.getValue("select permissionid from permissions_projects_users where projectid=%i and userid=%i" % (self.id, user.id))
        if not p: return None
        else:
            return permissions.ProjectPermission.get(p)
                        
            
class Batch(Cachable):
    __table__ = 'batches'
    __idcolumn__ = 'batchid'
    def __init__(self, db, id, project=None):
        Cachable.__init__(self, db, id)
        for prop in "name", "insertDate", "query":
            self.addDBProperty(prop)
        self.addDBProperty("insertUser", "insertuserid", user.users(self.db).getUser)
        self.addDBProperty("project", "projectid", func=partial(Project, db))
        self.addDBFKProperty("articles", "articles", "articleid", function=lambda aid: article.fromDB(self.db, aid))
        if project is not None:
            self.cacheValues(project=project)

def getAid(art):
    if type(art) == int: return art
    return art.id

class StoredResult(Cachable):
    __table__ = 'storedresults'
    __idcolumn__ = 'storedresultid'
    def __init__(self, db, id):
        Cachable.__init__(self, db, id)
        self.addDBProperty("name")
        self.addDBProperty("project", "projectid", func=partial(Project, db))
        self.addDBProperty("owner", "ownerid", user.users(self.db).getUser)
        self.addDBFKProperty("articles", "storedresults_articles","articleid", function=lambda aid: article.fromDB(self.db, aid))
    def addArticles(self, articles):
        self.db.insertmany("storedresults_articles", ["storedresultid", "articleid"],
                           [(self.id, getAid(a)) for a in articles])
        self.removeCached("articles")
        
        

        
if __name__ == '__main__':
    import dbtoolkit
    p = StoredResult(dbtoolkit.amcatDB(), 688)
    print p.name
    print p.project.name
    print len(p.articles)
    p.addArticles([42615480, 42660818, 42549384, 42691728, 42526488])
    print len(p.articles)
    p.db.conn.commit()
