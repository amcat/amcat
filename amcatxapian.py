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
                
    def getAid(self, document):
        if type(document) == int:
            document = self.index.get_document(document)
        return int(document.get_data())        
            
    def getArticle(self, document):
        return article.Article(self.db, self.getAid(document))

    def query(self,  query, returnWeights=False, returnAID=False, subset=None):  
        if type(query) in (str, unicode):
            query = self.parse(query)
        enquire = xapian.Enquire(self.index)
        enquire.set_query(query)
        matches = enquire.get_mset(0,self.index.get_doccount())
        #if subset: subset = set((a if type(a)==int else a.id) for a in subset)
        for m in matches:
            aid = self.getAid(m.docid) 
            if subset and aid not in subset: continue
            if not returnAID: aid = article.Article(self.db, aid)
            if returnWeights:
                yield aid, m.weight
            else:
                yield aid
                   
    def queries(self, queries, subset=None, **options):
        if subset: subset = set((a if type(a)==int else a.id) for a in subset)
        for q in queries:
            for a in self.query(q, subset=subset, **options):
                if type(a) == tuple:
                    yield (q,) + a
                else:
                    yield q, a         
       
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
            a = article.Article(db, a)
        try:
            txt = toolkit.stripAccents(a.text).encode('ascii', 'replace')
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
    import sys, dbtoolkit, project
    db = dbtoolkit.amcatDB()
    i = Index("/home/amcat/indices/draft", db)
    b = project.Batch(db, 4796)
    subset = b.articles
    queries = "yakult", "dsb", "heineken", "liander"
    for q, a, w in i.queries(queries, returnWeights=True, subset=subset):
        print q, `a`, w
        

