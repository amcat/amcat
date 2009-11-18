import xapian, article, toolkit, sqlalchemy, dbtoolkit 

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
        print self._aidmap
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
            yield self.getArticle(d)

    def getArticle(self, document):
        if type(document) == int:
            document = self.index.get_document(document)
        aid = int(document.get_data())
        return article.fromDB(self.db, aid)
        

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

    def query(self,  query, returnWeights=False):
        q = xapian.Query(query)
        enquire = xapian.Enquire(self.index)
        enquire.set_query(q)
        matches = enquire.get_mset(0,self.index.get_doccount())
        for m in matches:
            a = self.getArticle(m.docid)
            if returnWeights:
                yield a, m.weight
            else:
                yield a
        

    def mapFrequencies(self, article, map):
        for term, freq in self.getFrequencies(article, raw=True):
            if term in map:
                map[term] = freq

def createIndex(indexloc, articles, db=None, stemmer="dutch"):
    
    database = xapian.WritableDatabase(indexloc, xapian.DB_CREATE_OR_OVERWRITE)
    indexer = xapian.TermGenerator()
    if stemmer:
        indexer.set_stemmer(xapian.Stem(stemmer))
    for a in articles:
        if type(a) == int:
            a = article.fromDB(db, a)
        txt = toolkit.stripAccents(a.toText()).encode('ascii', 'replace')
        doc = xapian.Document()
        doc.set_data(str(a.id))
        indexer.set_document(doc)
        indexer.index_text(txt)
        database.add_document(doc)
    return Index(indexloc, db)

                
if __name__ == '__main__':
    import sys, dbtoolkit
    if len(sys.argv) <= 1:
        toolkit.warn("Usage: python amcatxapian.py INDEXLOC [QUERY] [< ARTICLEIDS]\n\nIf QUERY is giving, query exsting index; otherwise, build new index from ARTICLEIDS")
        sys.exit(1)
        
    indexloc = sys.argv[1]
    query = " ".join(sys.argv[2:])
    if query.strip():
        toolkit.warn("Querying index %s with %r" % (indexloc, query))
        i = Index(indexloc, dbtoolkit.amcatDB())
        for a, weight in i.query(query, returnWeights=True):
            print a.id, weight
    else:
        toolkit.warn("Creating new xapian index (database) at %s" % indexloc)
        articles = toolkit.tickerate(toolkit.intlist())
        i = createIndex(indexloc, articles)
        toolkit.warn("Created index %s" % i)

