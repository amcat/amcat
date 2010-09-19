from cachable import Cachable, DBPropertyFactory, ForeignKey
import permissions
from functools import partial
import user, article, project

class Batch(Cachable):
    __table__ = 'batches'
    __idcolumn__ = 'batchid'
    __dbproperties__ = ["name", "insertDate", "query"]
    insertUser = DBPropertyFactory("insertuserid", factory = lambda : user.User)
    project = DBPropertyFactory("projectid", factory = lambda : project.Project)
    articles = ForeignKey(lambda:article.Article)
    def __init__(self, *args, **kargs):
        Cachable.__init__(self, *args, **kargs)
        
def createBatch(project, name, query, db=None):
    if db is None: db = project.db
    if type(project) <> int: project = project.id
    batchid = db.insert('batches', dict(name=name, projectid=project, query=query))
    return Batch(db, batchid)
                        

if __name__ == '__main__':
    import dbtoolkit
    p = Batch(dbtoolkit.amcatDB(), 5271)
    print p.id, p.name, p.project
