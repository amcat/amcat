"""
Objectfinder module. Helps using several kinds of indices through one common interface.
"""

import lucenelib

class ObjectFinder:
    index = None
    languageid = None
    def __init__(self, index, languageid=101):
        self.index = index
        self.languageid = languageid

    def search(self, object):
        abstract

    def searchMultiple(self, objects):
        abstract

class LuceneFinder(ObjectFinder):
    def search(self, object):
        query = object.getSearchString(xapian=False, languageid=self.languageid)
        results = lucenelib.search(self.index, {"X" : query}.items())
        for aid in results[0]["X"].keys():
            yield article.Article(self.db, aid)

    def searchMultiple(self, objects):
        query = dict((o.id, o.getSearchString(xapian=False, languageid=self.languageid)) for o in objects)
        return lucenelib.search(self.index, query.items())[0]

class XapianFinder(ObjectFinder):
    def search(self, object):
        query = object.getSearchString(xapian=True, languageid=self.languageid)
        return self.index.query(query, acceptPhrase=True)

    def searchMultiple(self, objects):
        return dict((o.id, set(self.index.query(o.getSearchString(xapian=True, languageid=self.languageid), returnAID=True))) for o in objects)
