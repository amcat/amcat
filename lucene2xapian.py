import toolkit
import xapian

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
        # TODO: test of de MUSTS voorkomen in zelfde document, de NOTS niet, en 1 van de MAYS/MUSTS deze node is
        if any(q.matches(node) for q in self.nots): return False
        #if not all(q.matches(node) for q in self.musts): return False
        return (any(q.matches(node) for q in self.mays) or
                any(q.matches(node) for q in self.musts))
    def xapian(self, index):
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
                          
            
class PhraseQuery(Query):
    def __init__(self, phrase, slop=0):
        self.phrase = phrase
        self.slop = slop
    def __repr__(self):
        return "PhraseQuery(%r, slop=%i)" % (self.phrase, self.slop)
    def matches(self, node):
        for offset, term in enumerate(self.phrase):
            n2 = node.tree.getNode(node.position+offset)
            if not (n2 and term.matches(n2)): return False
        return True
    def xapian(self, index):
        p = xaps(self.phrase, index)
        if self.slop:
            return xapian.Query(xapian.Query.OP_NEAR, p, self.slop)
        else:
            return xapian.Query(xapian.Query.OP_PHRASE, p)
    
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

CLASSPATH=".:/home/amcat/resources/jars/lucene-core-2.3.2.jar:/home/amcat/libjava"
    
def convert(queries, index):
    args = ['"%s"' % q.replace('"','\\"') for q in queries]
    CMD = 'CLASSPATH=%s java AnokoQueryParser %s' % (CLASSPATH, " ".join(args))
    out, err =  toolkit.execute(CMD)
    if err: raise("Exception on parsing queries:\n%s\n------------\n" % (err))
    for query in out.split("\n"):
        yield eval(query).xapian(index)

if __name__ == '__main__':
    import sys, amcatxapian, dbtoolkit
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
    

