from cachable2 import Cachable, DBProperty, DBProperties, ForeignKey
import user, permissions, article
from functools import partial
import batch, codingjob, toolkit


class Project(Cachable):
    __table__ = 'projects'
    __idcolumn__ = 'projectid'
    __labelprop__ = 'name'

    name, insertDate, description = DBProperties(3)
    batches = ForeignKey(lambda: batch.Batch)
    #visibility = DBProperty(func=permissions.ProjectVisibility.get, table="project_visibility")
    insertUser = DBProperty(lambda : user.User, getcolumn="insertuserid")
    users = ForeignKey(lambda : user.User, table="permissions_projects_users")
    codingjobs = ForeignKey(lambda : codingjob.CodingJob)

    @property
    @toolkit.deprecated
    def href(self):
        return '<a href="projectDetails?projectid=%i">%i - %s</a>' % (self.id, self.id, self.name)
    
    @property
    @toolkit.deprecated
    def articles(self):
        for b in self.batches:
            for a in b.articles:
                yield a

    @toolkit.deprecated
    def userPermission(self, user):
        p = self.db.getValue("select permissionid from permissions_projects_users where projectid=%i and userid=%i" % (self.id, user.id))
        if not p: return None
        else:
            return permissions.ProjectPermission.get(p)       

@toolkit.deprecated
def Batch(*args, **kargs):
    """B{Deprecated: use L{batch.Batch}}"""
    return batch.Batch(args, kargs)

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
    
    name = DBProperty()
    project = DBProperty(lambda : Project)
    owner = DBProperty(lambda : user.User, getcolumn = "ownerid")
    articles = ForeignKey(lambda : article.Article, table="storedresults_articles")
    
    def addArticles(self, articles):
        self.db.insertmany("storedresults_articles", ["storedresultid", "articleid"],
                           [(self.id, getAid(a)) for a in articles])
        self.removeCached("articles")
    

        
if __name__ == '__main__':
    import dbtoolkit
    p = Project(dbtoolkit.amcatDB(), 1)
    batch = p.batches[0]
    print "--------"
    pr = batch.project
    print `p`
    print `batch`
    print `pr`
    print len(batch.articles)
    print p == pr
    print p is pr
