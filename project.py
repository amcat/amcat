from cachable2 import Cachable, DBProperty, DBProperties, ForeignKey
import user, permissions, article
from functools import partial
import batch, codingjob, toolkit, article


class Project(Cachable):
    __table__ = 'projects'
    __idcolumn__ = 'projectid'
    __labelprop__ = 'name'

    name, projectid, insertDate, description = DBProperties(4)
    articles = ForeignKey(lambda: article.Article)
    sets = ForeignKey(lambda : Set)
    insertUser = DBProperty(lambda : user.User, getcolumn="insertuserid")
    users = ForeignKey(lambda : user.User, table="permissions_projects_users")
    codingjobs = ForeignKey(lambda : codingjob.CodingJob)
    
class Set(Cachable):
    __table__ = 'sets'
    __idcolumn__ = 'setid'
    __labelprop__ = 'name'
    
    name = DBProperty()
    project = DBProperty(lambda : Project)
    articles = ForeignKey(lambda : article.Article, table="storedresults_articles")
    
    def addArticles(self, articles):
        self.db.insertmany("storedresults_articles", ["storedresultid", "articleid"],
                           [(self.id, getAid(a)) for a in articles])
        self.removeCached("articles")
    

        
if __name__ == '__main__':
    import dbtoolkit
    p = Project(dbtoolkit.amcatDB(), 1)
    print p.getType("name")
    print Project.name.getType()
