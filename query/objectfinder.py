"""
Objectfinder module. Helps using several kinds of indices through one common interface.
"""

import lucenelib, article

class ObjectFinder(object):
    def __init__(self, index, languageid=101):
        self.index = index
        self.languageid = languageid

    def search(self, object):
        abstract

    def searchMultiple(self, objects):
        abstract

class LuceneFinder(ObjectFinder):
    def __init__(self, db, index, languageid=101):
        ObjectFinder.__init__(self, index, languageid)
        self.db = db
    def search(self, object):
        query = object.getSearchString(xapian=False, languageid=self.languageid)
        results = lucenelib.search(self.index, {"X" : query}.items())
        return results[0]["X"].iterkeys()

    def searchMultiple(self, objects):
        query = dict((o.id, o.getSearchString(xapian=False, languageid=self.languageid)) for o in objects)
        for k,v in (lucenelib.search(self.index, query.items())[0]).iteritems():
            yield k, v.keys()

class XapianFinder(ObjectFinder):
    def search(self, object):
        query = object.getSearchString(xapian=True, languageid=self.languageid)
        return self.index.query(query, acceptPhrase=True)

    def searchMultiple(self, objects):
        return dict((o.id, set(self.index.query(o.getSearchString(xapian=True, languageid=self.languageid), returnAID=True))) for o in objects)

    
if __name__ == '__main__':
    import ont, dbtoolkit

    db = dbtoolkit.amcatDB()
    lf = LuceneFinder(db, "/home/amcat/indices/AEX kranten JK 2007-09-24T10:32:18/", 13)
    o = ont.Object(db, 1249)
    print list(lf.search(o))
    o2 = ont.Object(db, 2423)
    print list(lf.searchMultiple([o, o2]))
