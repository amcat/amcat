"""
Objectfinder module. Helps using several kinds of indices through one common interface.
"""

import lucenelib, article, ont, toolkit, xapian
import logging; log = logging.getLogger(__name__)

class ObjectFinder(object):
    def __init__(self, index, languageid=101):
        self.index = index
        self.languageid = languageid

    def search(self, object):
        abstract

    def searchMultiple(self, objects):
        abstract

    def getTerms(self, document):
        abstract

    def getQueries(self, objects):
        if type(objects) in (ont.Object, ont.BoundObject):
            return self.getQuery(objects)
        queries = map(self.getQuery, objects)
        queries = [q for q in queries if q]
        if not queries: return None
        return "(%s)" % ") OR (".join(queries)

    def searchOnTerm(self, query):
        abstract

class LuceneFinder(ObjectFinder):
    def search(self, objects):
        query = self.getQueries(objects)
        results, time, n = lucenelib.search(self.index, {"X" : query}.items())
        return results["X"].iterkeys()

    def searchMultiple(self, objectlist):
        query = {}
        for o, objects in objectlist:
            q = self.getQueries(objects)
            if q: query[o.id] = q
        results, time, n = lucenelib.search(self.index, query.items())
        for k,v in results.iteritems():
            yield k, v.keys()

    def getQuery(self, obj):

            
        query = obj.getSearchString(xapian=False, languageid=self.languageid, fallback=True)
        return query

    def getTerms(self, document):
        raise Exception("Not yet implemented")

    def searchOnTerm(self, query):
        log.info('Search for query %s' % query)
        results, time, n = lucenelib.search(self.index, {"X" : query}.items())
        return results["X"].iterkeys()

class XapianFinder(ObjectFinder):
    def search(self, objects, verbose=False):
        try:
            objects = list(objects)
        except:
            objects = [objects]
        query = self.getQueries(objects)
        if not query:
            toolkit.warn("Empty query for %r/%s" % (objects, objects))
            return []
        q= list(self.index.query(query, acceptPhrase=True, returnAID=True))
        return q

    def searchMultiple(self, objectlist):
        for o, objects in objectlist:
            yield o.id, self.search(objects)#, verbose=o.id == 17538)

        #return ((o.id, set(self.index.query(o.getSearchString(xapian=True, languageid=self.languageid), returnAID=True))) for o in objects)

    def getQuery(self, obj):
        query = obj.getSearchString(xapian=True, languageid=self.languageid, fallback=True)
        return query

    def getTerms(self, document):
        for term in self.index.getDocument(document).termlist():
            yield term[0]

    def searchOnTerm(self, query):
        terms = [x.lower() for x in query.split()]
        
        query = xapian.Query(xapian.Query.OP_AND, terms)
        for art in self.index.query(query, returnAID=True):
            yield art

if __name__ == '__main__':
    import ont, dbtoolkit

    db = dbtoolkit.amcatDB()
    lf = LuceneFinder("/home/amcat/indices/AEX kranten JK 2007-09-24T10:32:18/", 13)
    o = ont.Object(db, 1545)
    print o
    print list(lf.search(o))
    #o2 = ont.Object(db, 2423)
    #print list(lf.searchMultiple([o, o2]))
