import ont, toolkit, re
import graph

class Recogniser(object):
    def __init__(self, db, objects, debug=None, lang=101):
        self.objects = objects
        #self.objects = set([ont.Object(db, 10275)])
        #self.objects = set([ont.Object(db, 1156)])
        self.queries = dict(getQueries(self.objects, lang=lang))

    def debug(self, msg):
        pass
        
    def matches(self, node, object):
        if object.name:
            w = str(node.word).lower()
            if object.name.lower() == w: return True
            
            if object.prefix:
                pref = " ".join(w.split(" ")[:-1])
                name = w.split(" ")[-1]
                if pref == object.prefix.lower() and name == object.name.lower(): return True

        q = self.queries.get(object)
        if not q: return False
        return q.matches(node)
            
        

    def getObjects(self, nodes):
        if isinstance(nodes, graph.Node): nodes = [nodes]
        try:
            for node in nodes:
                for obj in self.objects:
                    if self.matches(node, obj):
                        yield obj
        except Exception, e:
            raise Exception("Error on getObjects(%r): %s" % (nodes, e))

def getActors(db):
    return set(ont.Object(db, oid) for (oid,) in db.doQuery(
            """select objectid from o_sets_objects o where setid = 307 and 
               (o.objectid in (select objectid from o_politicians) or 
                o.objectid in (select childid from o_hierarchy where classid=4000 and parentid = 13898))"""))

def getIssues(db):
    #laf!
    return set(ont.Object(db, oid) for (oid,) in db.doQuery(
            "select objectid from o_labels where languageid=101"))

def getRecogniser(db):
    return Recogniser(db, getActors(db) | getIssues(db))

def getWord(node_or_word):
    if type(node_or_word) in (str, unicode): return node_or_word.lower()
    return str(node_or_word.word).lower()

class Query(object):
    def matches(self, node):
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
            
class PhraseQuery(Query):
    def __init__(self, phrase, slop=0):
        self.phrase = phrase
        self.slop = slop
    def __repr__(self):
        return "PhraseQuery(%r, slop=%i)" % (self.phrase, self.slop)
    def matches(self, node):
        for offset, term in enumerate(self.phrase):
            n2 = node.getNeighbour(offset)
            if not (n2 and term.matches(n2)): return False
        return True
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

CLASSPATH=".:/home/amcat/resources/jars/lucene-core-2.3.2.jar:/home/amcat/resources/jars/msbase.jar:/home/amcat/resources/jars/mssqlserver.jar:/home/amcat/resources/jars/msutil.jar:/home/amcat/libjava:/home/amcat/resources/jars/lucene-highlighter-2.3.2.jar:/home/amcat/resources/jars/aduna-clustermap-2006.1.jar:/home/amcat/resources/jars/jutf7-0.9.0.jar:/home/amcat/resources/jars/stanford-parser-2008-10-30.jar"
    
def getQueries(objects, lang=101):
    objs = []
    args = []
    for o in objects:
        l = o.labels.get(lang)
        if not l: continue
        objs.append(o)
        args.append('"%s"' % l.replace('"', '\\"'))
    CMD = 'CLASSPATH=%s java AnokoQueryParser %s' % (CLASSPATH, " ".join(args))
    out, err =  toolkit.execute(CMD)
    if err: raise("Exception on parsing queries:\n%s\n------------\n" % (err))
    for obj, query in zip(objs, out.split("\n")):
        yield obj, eval(query)
    
                              
    
    
if __name__ == '__main__':


    import dbtoolkit
    db = dbtoolkit.amcatDB()
    r = Recogniser(db)
    for o, q in r.queries.items():
        if type(q) == BooleanQuery and type(q.nots) not in (list, tuple): raise Exception([o, q])

    p = parsetree.fromDB(db, 43729648)
    for n in p.getNodes():
        if n.word.label.lower() == 'partij':
            print list(r.getObjects(n))
            
    

