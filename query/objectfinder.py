"""
Objectfinder module. Helps using several kinds of indices through one common interface.
"""

import lucenelib, article, ont

class ObjectFinder(object):
    def __init__(self, index, languageid=101):
        self.index = index
        self.languageid = languageid

    def search(self, object):
        abstract

    def searchMultiple(self, objects):
        abstract

    def getQueries(self, objects):
        if type(objects) in (ont.Object, ont.BoundObject): query = self.getQuery(objects)
        queries = map(self.getQuery, objects)
        queries = [q for q in queries if q]
        if not queries: return None
        return "(%s)" % ") OR (".join(queries)
        
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
        return obj.getSearchString(xapian=False, languageid=self.languageid, fallback=True)


class XapianFinder(ObjectFinder):
    def search(self, objects):
        objects=list(objects)
        query = self.getQueries(objects)
        print object, query
        if not query: raise("Empty query for %r/%s" % (objects, objects))
        return self.index.query(query, acceptPhrase=True, returnAID=True)

    def searchMultiple(self, objects):
        return ((o.id, set(self.index.query(o.getSearchString(xapian=True, languageid=self.languageid), returnAID=True))) for o in objects)

    def getQuery(self, obj):
        return obj.getSearchString(xapian=True, languageid=self.languageid, fallback=True)
    
if __name__ == '__main__':
    import ont, dbtoolkit

    db = dbtoolkit.amcatDB()
    lf = LuceneFinder("/home/amcat/indices/AEX kranten JK 2007-09-24T10:32:18/", 13)
    o = ont.Object(db, 1545)
    print o
    print list(lf.search(o))
    #o2 = ont.Object(db, 2423)
    #print list(lf.searchMultiple([o, o2]))
