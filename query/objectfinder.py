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

LTIME = 0.
class LuceneFinder(ObjectFinder):
    def search(self, object):
        query = object.getSearchString(xapian=False, languageid=self.languageid, fallback=True)
        #print "search", object, object.id , query
        #print "obj:", object
        #print "lang:", self.languageid, "query:", query
        results, time, n = lucenelib.search(self.index, {"X" : query}.items())
        global LTIME; LTIME +=  time
        return results["X"].iterkeys()

    def searchMultiple(self, objectlist):
        query = {}
        for o, objects in objectlist:
            q = self.getQueries(objects)
            if q: query[o.id] = q

        #print "lang:", self.languageid, "query:", query
        results, time, n = lucenelib.search(self.index, query.items())
        global LTIME; LTIME +=  time            
        for k,v in results.iteritems():
            yield k, v.keys()

    def getQueries(self, objects):
        if type(objects) == ont.Object: query = self.getQuery(objects)
        queries = map(self.getQuery, objects)
        queries = [q for q in queries if q]
        if not queries: return None
        return "(%s)" % ") OR (".join(queries)
    def getQuery(self, obj):
        return obj.getSearchString(xapian=False, languageid=self.languageid, fallback=True)


class XapianFinder(ObjectFinder):
    def search(self, object):
        query = object.getSearchString(xapian=True, languageid=self.languageid)
        return self.index.query(query, acceptPhrase=True)

    def searchMultiple(self, objects):
        return dict((o.id, set(self.index.query(o.getSearchString(xapian=True, languageid=self.languageid), returnAID=True))) for o in objects)

    
if __name__ == '__main__':
    import ont, dbtoolkit

    db = dbtoolkit.amcatDB()
    lf = LuceneFinder("/home/amcat/indices/AEX kranten JK 2007-09-24T10:32:18/", 13)
    o = ont.Object(db, 1545)
    print o
    print list(lf.search(o))
    #o2 = ont.Object(db, 2423)
    #print list(lf.searchMultiple([o, o2]))
