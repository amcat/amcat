from amcat.tools.cachable.cachable import Cachable, DBProperty, DBProperties, ForeignKey
from amcat.tools.cachable.latebind import LB

class Set(Cachable):
    __table__ = 'sets'
    __idcolumn__ = 'setid'
    __labelprop__ = 'name'
    
    name, setid = DBProperties(2)
    project = DBProperty(LB("Project"))
    articles = ForeignKey(LB("Article"), table="sets_articles")
    owner = DBProperty(LB("User"), getcolumn="ownerid")

    def addArticles(self, articles):
        self.db.insertmany("storedresults_articles", ["storedresultid", "articleid"],
                           [(self.id, getAid(a)) for a in articles])
        self.removeCached("articles")
    
