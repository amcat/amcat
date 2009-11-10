import xapian, article

class Index(object):
    def __init__(self, location, db, stem=True):
        self.location = location
        self.index = xapian.Database(location)
        self.db = db
        self._aidmap = None
        self.stem=stem

    def _getAidmap(self):
        if self._aidmap is None:
            self._aidmap = {}
            for d in self.documents:
                self._aidmap[int(d.get_data())] = d.get_docid()
        return self._aidmap
    
    def getDocumentID(self, article):
        if type(article) <> int:
            article = article.id
        return self._getAidmap()[article]
    
    def getDocument(self, article):
        return self.index.get_document(self.getDocumentID(article))
    
    @property
    def documents(self):
        for i in range(1, self.index.get_lastdocid() + 1):
            yield self.index.get_document(i)
    
    @property
    def articles(self):
        for d in self.documents:
            aid = int(d.get_data())
            yield article.fromDB(self.db, aid)

    def getFrequencies(self, article=None, raw=False):
        if article:
            docid = self.getDocumentID(article)
            list = self.index.termlist(docid)
        else:
            list = self.index.allterms()
                
        for t in list:
            term = t.term
            if not raw:
                if self.stem:
                    if term[0] <> 'Z': continue
                    term = term[1:]
                else:
                    if term[0] == 'Z': continue
            if article:
                yield term, t.wdf
            else:
                yield term, t.termfreq

    def mapFrequencies(self, article, map):
        for term, freq in self.getFrequencies(article, raw=True):
            if term in map:
                map[term] = freq

if __name__ == '__main__':
    import sys, dbtoolkit
    i = Index(sys.argv[1], dbtoolkit.amcatDB())
    #a = article.fromDB(i.db, 42577134)
    #print "Database content: \n----\n%s\n-----" % a.toText()
    #map = {'Zfraud' : 0, 'Zgevall' : 0}
    #i.mapFrequencies(a, map)
    #print map
    for t, f in i.getFrequencies(raw=True):
        print t, f
    
