import ont, toolkit, re
import graph
from itertools import imap, izip

class Recogniser(object):
    def __init__(self, db, objects, debug=None, querylang=101):
        self.objects = objects
        #self.objects = set([ont.Object(db, 10275)])
        #self.objects = set([ont.Object(db, 1156)])
        self.queries = dict(getQueries(self.objects, querylang=querylang))

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


class Query(object):
    def matches(self, words, context=[]):
        abstract
class BooleanQuery(Query):
    def __init__(self, mays=[], musts=[], nots=[]):
        self.mays = mays
        self.musts = musts
        self.nots = nots
    def __repr__(self):
        return "BooleanQuery(mays=%r, musts=%r, nots=%s)" % (self.mays, self.musts, self.nots)
    def matches(self, word, context=[]):
        # return False if none of the mays/musts matches the current word
        # return False if any context-word matches one of the nots
        # return False if any of the musts is not found in the context
        # return True otherwise
        word = getWord(word)
        if not any(q.matches(word, context) for q in set(self.mays) | set(self.musts)):
            return False
        for q in self.nots:
            if any(q.matches(w, context) for w in context):
                return False
        for q in self.musts:
            if not any(q.matches(w, context) for w in context):
                return False
        return True
            
class PhraseQuery(Query):
    def __init__(self, phrase, slop=0):
        self.phrase = phrase
        self.slop = slop
    def __repr__(self):
        return "PhraseQuery(%r, slop=%i)" % (self.phrase, self.slop)
    def matches(self, word, context=[]):
        # anchor to first word in phrase
        word = getWord(word)
        if not self.phrase[0].matches(word, context): return False
        if self.slop:
            # TODO: consider as AND
            for q in self.phrase:
                if not any(q.matches(w, context) for w in context): return False
            return True
        else:
            context = map(getWord, context)
            if word not in context: raise Exception("%r not in %r??" % (word, context))
            words = context[map(getWord, context).index(word):]
            if len(words) < len(self.phrase): return False
            for word, q in zip(words, self.phrase):
                if not q.matches(word, context): return False
            return True
    
class Term(Query):
    def __init__(self, term):
        self.term = term.lower()
    def __repr__(self):
        return "Term(%r)" % self.term
    def matches(self, word, context=[]):
        word = getWord(word)
        if "*" not in self.term: return word == self.term
        if "*" not in self.term[:-1]: return word.startswith(self.term[:-1])
        return bool(re.match(self.term.replace("*", ".*")+"$", word))

def getWord(word):
    return str(word).lower()
    
CLASSPATH=".:/home/amcat/resources/jars/lucene-core-2.3.2.jar:/home/amcat/resources/jars/msbase.jar:/home/amcat/resources/jars/mssqlserver.jar:/home/amcat/resources/jars/msutil.jar:/home/amcat/libjava:/home/amcat/resources/jars/lucene-highlighter-2.3.2.jar:/home/amcat/resources/jars/aduna-clustermap-2006.1.jar:/home/amcat/resources/jars/jutf7-0.9.0.jar:/home/amcat/resources/jars/stanford-parser-2008-10-30.jar"

def lucene2terms(queries):
    args = ['"%s"' % q.replace('"', '\\"') for q in queries]
    CMD = 'CLASSPATH=%s java AnokoQueryParser %s' % (CLASSPATH, " ".join(args))
    out, err =  toolkit.execute(CMD)
    if err: raise("Exception on parsing queries:\n%s\n------------\n" % (err))
    if out[-1] == "\n": out = out[:-1]
    
    return map(eval, out.split("\n"))

    
def getQueries(objects, querylang=101):
    objs = []
    queries = []
    for o in objects:
        q = o.labels.get(querylang)
        if not q: continue
        objs.append(o)
        queries.append(q)
    return izip(objs, lucene2terms(queries))
    
if __name__ == '__main__':
    import sys
    print list(lucene2terms(sys.argv[1:]))

