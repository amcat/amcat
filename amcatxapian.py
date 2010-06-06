import xapian, article, toolkit,  dbtoolkit, re, word
from functools import partial

VALUE_AID = 1

class Index(object):
    def __init__(self, location, db=None, stem=True):
        self.location = location
        self._index = None
        self.db = db
        self._aidmap = None
        self.stem=stem


    @property
    def index(self):
        if '_index' not in self.__dict__ or self._index is None:
            if not self.location: raise Exception("No index present and no location given")
            #print ">>>>>>", `self.location`
            self._index = xapian.Database(self.location)
        return self._index
    
        
    def __getstate__(self):
        d = self.__dict__
        for delprop in '_index', '_aidmap':
            if delprop in d: del d[delprop]
        return d

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

    def expand(self, prefix):
        return xapian.Query(xapian.Query.OP_OR, [t.term for t in self.index.allterms(prefix)])

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

    def query(self,  query, returnWeights=False, returnAID=False, subset=None, acceptPhrase=True):
        if type(query) in (str, unicode):
            query = self.parse(query, acceptPhrase)

        enquire = xapian.Enquire(self.index)
        enquire.set_query(query)
        matches = enquire.get_mset(0,self.index.get_doccount())
        if subset: subset = set((a if type(a)==int else a.id) for a in subset)
        for m in matches:
            try:
                aid = self.getAid(m.docid)
            except:
                continue 
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

    def parse(self, query, acceptPhrase=False):
        qp = xapian.QueryParser()
        qp.set_database(self.index)
        flags = xapian.QueryParser.FLAG_WILDCARD
        flags |= xapian.QueryParser.FLAG_BOOLEAN
        flags |= xapian.QueryParser.FLAG_LOVEHATE
        if acceptPhrase:
            flags |= xapian.QueryParser.FLAG_PHRASE
        return qp.parse_query(query, flags)
                
# TermGenerators: move this out of the class?
    
class BrouwersGenerator(object):
    def __init__(self, db, prop=None):
        self.wordcache = word.WordCache(db)
        self.wg = WordGenerator()
        self.prop = prop
    def getTerms(self, article):
        for word in self.wg.getTerms(article):
            for b in self.wordcache.getBrouwersCats(word, self.prop):
                if not b: continue
                if self.prop is None:
                    yield str(b.id)
                else:
                    yield b.replace(" ","_")
    
            
class WordGenerator(object):
    def getTerms(self, article):
        for word in article.words():
            word = toolkit.stripAccents(word).encode('ascii', 'replace').lower()
            if not re.match("[A-Za-z]+", word): word = "#"
            yield word
            
class NGramGenerator(object):
    def __init__(self, n, wordgenerator=None):
        self.n = n
        self.wordgenerator = wordgenerator or WordGenerator()
    def getTerms(self, article):
        last = [""] * (self.n)
        for word in self.wordgenerator.getTerms(article):
            last.append(word)
            del(last[0])
            if self.n == 1:
                yield last[0]
            else:
                yield "N%i_%s" % (self.n, "_".join(last))

# until here?

def createIndex(indexloc, articles, db=None, stemmer="dutch", termgenerators=None, append=False):
    if not append:
        database = xapian.WritableDatabase(indexloc, xapian.DB_CREATE_OR_OVERWRITE)
    else:
        database = xapian.WritableDatabase(indexloc, xapian.DB_CREATE_OR_OPEN)

    indexer = xapian.TermGenerator()
    if stemmer:
        indexer.set_stemmer(xapian.Stem(stemmer))
    for a in articles:
        if type(a) == int:
            a = article.Article(db, a)
        try:
            #txt = toolkit.stripAccents(a.text).encode('ascii', 'replace')
            txt = toolkit.stripAccents(a.fulltext()).encode('ascii', 'replace')
        except Exception, e:
            toolkit.warn("Error on indexing %i: %s" % (a.id, e))
            continue
        doc = xapian.Document()
        doc.set_data(str(a.id))
        doc.add_value(VALUE_AID, "%020i" % a.id)
        indexer.set_document(doc)
        if termgenerators:
            if type(termgenerators) not in (list, tuple, set):
                termgenerators = [termgenerators]
            for tg in termgenerators:
                txt = ' '.join(tg.getTerms(a))
                indexer.index_text(txt)
        else:
            indexer.index_text(txt)
        
        database.add_document(doc)
    database.flush()
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
        i = createIndex(indexloc, articles,dbtoolkit.amcatDB())
        toolkit.warn("Created index %s" % i)
