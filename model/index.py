from cachable import Cachable
import lucenelib
import article

class Index(Cachable):
    __table__ = 'indices'
    __idcolumn__ = 'indexid'
    __dbproperties__ = ["name", "directory"]


    def query(self, terms, **options):
        """Executes the query on the index and yields articles"""
        if type(terms) in (str, unicode): terms = [terms]
        aidsDict, time, hits = lucenelib.search(self.directory, list(enumerate(terms)), db=self.db, **options)
        for id, dict in aidsDict.iteritems():
            for aid in dict.keys():
                yield article.Article(self.db, aid)


        
        
