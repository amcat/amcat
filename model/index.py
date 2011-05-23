from amcat.tools.cachable.cachable import Cachable, ForeignKey, DBProperty, DBProperties
from amcat.tools.cachable.latebind import LB
#import lucenelib
from amcat.model import article

class Index(Cachable):
    __table__ = 'indices'
    __idcolumn__ = 'indexid'
    __labelprop__ = "name"

    name, status, started,done, directory, options = DBProperties(6)
    set = DBProperty(LB("Set"), getcolumn="storedresultid")

    def query(self, terms, **options):
        """Executes the query on the index and yields articles"""
        if type(terms) in (str, unicode): terms = [terms]
        aidsDict, time, hits = lucenelib.search(self.directory, list(enumerate(terms)), db=self.db, **options)
        for id, dict in aidsDict.iteritems():
            for aid in dict.keys():
                yield article.Article(self.db, aid)


        
        
