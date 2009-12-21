import xapian, article, toolkit, sqlalchemy, dbtoolkit 

VALUE_AID = 1

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
        #print self._aidmap
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

    def getAid(self, document):
        if type(document) == int:
            document = self.index.get_document(document)
        return int(document.get_data())        
            
    def getArticle(self, document):
        return article.Article(self.db, self.getAid(document))
        

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

    def query(self,  query, returnWeights=False, returnAID=False, subset=None):
        if type(query) in (str, unicode):
            query = self.parse(query)
        enquire = xapian.Enquire(self.index)
        enquire.set_query(query)
        matches = enquire.get_mset(0,self.index.get_doccount())
        articlefunc = self.getAid if returnAID else self.getArticle
        for m in matches:
            a = articlefunc(m.docid)
            if returnWeights:
                yield a, m.weight
            else:
                yield a
                
    def queryCount(self,  query):
        i = 0
        for x in self.query(query):
            i += 1
        return i
        
    def mapFrequencies(self, article, map):
        for term, freq in self.getFrequencies(article, raw=True):
            if term in map:
                map[term] = freq

    def parse(self, query):
        qp = xapian.QueryParser()
        qp.set_database(self.index)
        return qp.parse_query(query, xapian.QueryParser.FLAG_WILDCARD)
                


def createIndex(indexloc, articles, db=None, stemmer="dutch"):
    
    database = xapian.WritableDatabase(indexloc, xapian.DB_CREATE_OR_OVERWRITE)
    indexer = xapian.TermGenerator()
    if stemmer:
        indexer.set_stemmer(xapian.Stem(stemmer))
    for a in articles:
        if type(a) == int:
            a = article.fromDB(db, a)
        try:
            txt = toolkit.stripAccents(a.toText()).encode('ascii', 'replace')
        except Exception, e:
            toolkit.warn("Error on indexing %i: %s" % (a.id, e))
            continue
        doc = xapian.Document()
        doc.set_data(str(a.id))
        doc.add_value(VALUE_AID, "%020i" % a.id)
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

