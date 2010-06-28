from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory
import user, permissions, article
from functools import partial

def projects(db, usr, own=1):
    if own:
        if type(usr) == int:
            usr = user.User(db, usr)
        for project in usr.projects:
            yield project
    else: # all projects
        userid = usr if type(usr) == int else usr.id
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

def getCodingJob(db, id):
    return codingjob.CodingJob(db, id)

class Project(Cachable):
    __table__ = 'projects'
    __idcolumn__ = 'projectid'
    __dbproperties__ = ["name", "insertDate", "description"]
    
    batches = DBFKPropertyFactory("batches", "batchid", factory = lambda: Batch)
    visibility = DBPropertyFactory(func=permissions.ProjectVisibility.get, table="project_visibility")
    insertUser = DBPropertyFactory("insertuserid", dbfunc = lambda db, id : user.User(db, id))
    users = DBFKPropertyFactory("permissions_projects_users", "userid", dbfunc=lambda db, id : user.User(db, id))
    codingjobs = DBFKPropertyFactory("codingjobs", "codingjobid", dbfunc=getCodingJob)

    @property
    def href(self):
        return '<a href="projectDetails?projectid=%i">%i - %s</a>' % (self.id, self.id, self.name)
    @property
    def articles(self):
        for b in self.batches:
            for a in b.articles:
                yield a

    def userPermission(self, user):
        p = self.db.getValue("select permissionid from permissions_projects_users where projectid=%i and userid=%i" % (self.id, user.id))
        if not p: return None
        else:
            return permissions.ProjectPermission.get(p)       
            
class Batch(Cachable):
    __table__ = 'batches'
    __idcolumn__ = 'batchid'
    __dbproperties__ = ["name", "insertDate", "query"]
    insertUser = DBPropertyFactory("insertuserid", dbfunc = lambda db, id : user.User(db, id))
    project = DBPropertyFactory("projectid", dbfunc=lambda db, id : Project(db, id))
    articles = DBFKPropertyFactory("articles", "articleid", dbfunc= lambda db, id : article.Article(db, id))
    def __init__(self, *args, **kargs):
        Cachable.__init__(self, *args, **kargs)

def getArticles(*objects):
    for object in objects:
        for a in object.articles:
            yield a
    
        
def getAid(art):
    if type(art) == int: return art
    return art.id

class StoredResult(Cachable):
    __table__ = 'storedresults'
    __idcolumn__ = 'storedresultid'
    __labelprop__ = 'name'
    name = DBPropertyFactory()
    project = DBPropertyFactory("projectid", dbfunc=lambda db, id : Project(db, id))
    owner = DBPropertyFactory("ownerid", dbfunc = lambda db, id: user.User(db, id))
    articles = DBFKPropertyFactory("storedresults_articles","articleid", dbfunc=lambda db, id: article.Article(db, id))
    
    def addArticles(self, articles):
        self.db.insertmany("storedresults_articles", ["storedresultid", "articleid"],
                           [(self.id, getAid(a)) for a in articles])
        self.removeCached("articles")
        

import codingjob # prevent import cycle

        
if __name__ == '__main__':
    import dbtoolkit
    p = Project(dbtoolkit.amcatDB(), 1)
    batch = p.batches[0]
    print "--------"
    pr = batch.project
    print `p`
    print `batch`
    print `pr`
    print p == pr
    print p is pr
