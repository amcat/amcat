import toolkit
import xapian
import re

def xaps(qs, index): return [q.xapian(index) for q in qs]

class Query(object):
    def matches(self, node):
        abstract
    def xapian(self):
        abstract
class BooleanQuery(Query):
    def __init__(self, mays=[], musts=[], nots=[]):
        self.mays = mays
        self.musts = musts
        self.nots = nots
    def __repr__(self):
        return "BooleanQuery(mays=%r, musts=%r, nots=%s)" % (self.mays, self.musts, self.nots)
    def matches(self, node):
        #print "%s matches %s?" % (self, node)
        if not (any(q.matches(node) for q in self.mays) or
                any(q.matches(node) for q in self.musts)):
            return False
        if any(matchesSentence(node.sentence, q) for q in self.nots): return False
        if not all(matchesSentence(node.sentence, q) for q in self.musts): return False
        return True

        if self.mays: mays = xapian.Query(xapian.Query.OP_OR, xaps(self.mays, index))
        if self.musts: musts = xapian.Query(xapian.Query.OP_AND, xaps(self.mays, index))        
        if self.mays and self.musts:
            q = xapian.Query(xapian.Query.OP_AND, mays, musts)
        elif self.mays:
            q = mays
        elif self.musts:
            q = musts
        else:
            raise Exception("Cannot handle pure NOT queries!")
        if self.nots:
            nots = xapian.Query(xapian.Query.OP_AND, xaps(self.nots, index))
            q = xapian.Query(xapian.Query.OP_AND_NOT, q, nots)
        return q
    def getWords(self, onlyglobs=False):
        for w in self.mays:
            for w2 in w.getWords(onlyglobs):
                yield w2
        
        for w in self.musts:
            for w2 in w.getWords(onlyglobs):
                yield w2
            
                          
            
class PhraseQuery(Query):
    def __init__(self, phrase, slop=0):
        self.phrase = phrase
        self.slop = slop
    def __repr__(self):
        return "PhraseQuery(%r, slop=%i)" % (self.phrase, self.slop)
    def matches(self, node):
        if self.slop:
            if not any(q.matches(node) for q in self.phrase): return False
            nodes = [node.getNeighbour(i) for i in range(self.slop+1)]
            for term in self.phrase:
                if not any(term.matches(n) for n in nodes): return False
        else:
            for offset, term in enumerate(self.phrase):
                n2 = node.getNeighbour(offset)
                if not (n2 and term.matches(n2)): return False
        return True
    def xapian(self, index):
        p = xaps(self.phrase, index)
        if self.slop:
            return xapian.Query(xapian.Query.OP_NEAR, p, self.slop)
        else:
            return xapian.Query(xapian.Query.OP_PHRASE, p)
    def getWords(self, onlyglobs=False):
        for w in self.phrase:
            for w2 in w.getWords(onlyglobs):
                yield w2

        
class Term(Query):
    def __init__(self, term):
        self.term = term.lower()
    def __repr__(self):
        return "Term(%r)" % self.term
    def matches(self, node):
        word = getWord(node)
        if "*" not in self.term: return word == self.term
        if "*" not in self.term[:-1]: return word.startswith(self.term[:-1])
        return bool(re.match(self.term.replace("*", ".*")+"$", word))
    def xapian(self, index):
        if self.term.endswith("*"):
            return index.expand(self.term[:-1])
        return xapian.Query(self.term)
    def getWords(self, onlyglobs=False):
        if onlyglobs and "*"not in self.term: return
        yield self.term.replace("*","")

def getWord(w):
    return str(w)

def matchesSentence(sentence, term):
    for word in sentence.words:
        if term.matches(word): return word

CLASSPATH=".:/home/amcat/resources/jars/lucene-core-2.3.2.jar:/home/amcat/libjava"

def getTerms(queries):
    args = ['"%s"' % q.replace('"','\\"') for q in queries]
    CMD = 'CLASSPATH=%s java AnokoQueryParser %s' % (CLASSPATH, " ".join(args))
    out, err =  toolkit.execute(CMD)
    if err: raise("Exception on parsing queries:\n%s\n------------\n" % (err))
    for query in out.split("\n"):
        if query.strip():
            yield eval(query)

def getTerm(query):
    return list(getTerms([query]))[0]
            
def convert(queries, index):
    for term in getTerms(queries):
        yield term.xapian(index)

if __name__ == '__main__':
    import sys, amcatxapian, dbtoolkit
    t = getTerm('"principe moskee/e*n"~5')
    import sentence
    db = dbtoolkit.amcatDB()
    s = sentence.Sentence(db, 4023713)
    for w in s.words:
        print "%-10s" % w, t.matches(w)
    sys.exit()
    
    index = sys.argv[1]
    i = amcatxapian.Index(index, dbtoolkit.amcatDB())
    lquery = sys.argv[2:]
    xquery = convert(lquery, i)
    for l,x in zip(lquery, xquery):
        toolkit.ticker.warn(l)
        #toolkit.ticker.warn(len(list(i.query(x, returnAID=True))))
        enquire = xapian.Enquire(i.index)
        enquire.set_query(x)
        matches = enquire.get_mset(0,i.index.get_doccount())
        toolkit.ticker.warn(len(matches))
    

