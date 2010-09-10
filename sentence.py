import dbtoolkit, toolkit, collections
from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory, CachingMeta
import cachable
from functools import partial
import article, word
import graph

class SentenceWord(graph.Node, Cachable):
    __table__ = 'parses_words'
    __idcolumn__ = ['sentenceid','wordbegin']
    __labelprop__ = 'word'
    word = DBPropertyFactory("wordid", dbfunc=word.Word)
    def __init__(self, *args, **kargs):
        Cachable.__init__(self, *args, **kargs)
        graph.Node.__init__(self)
    @property
    def sentence(self):
        return Sentence(self.db, self.id[0])
    def getGraph(self):
        return self.sentence

    def __str__(self):
        return "%i:%s" % (self.position, self.word)
    
    @property
    def position(self):
        return self.id[1]
    def getNeighbour(self, offset=1):
        return self.sentence.getWord(self.position + offset)
    
def getSentenceWord(sentence, position):
    return SentenceWord(sentence.db, (sentence.id, position))
    
def getTriple(sent, parent, rel, child, analysisid):
    parent, child = map(sent.getWord, (parent, child))
    rel = Relation(sent.db, rel)
    return parent, rel, child, analysisid
    #print sent, parent, child, rel

NEED_COPULA_FLIP_ANALYSISIDS = 4,
COPULA_RELID=58
KEEP_ON_NOUN_RELIDS = 4,51, 55 # amod, det, nn

def flipCopula(triples):
    """Flip the copula relations for stanford parses as I think they make no sense whatsoever"""
    toflip = []
    if type(triples) <> set: raise Exception(triples)
    for parent, rel, child in triples:
        if rel.id == COPULA_RELID:
            toflip.append((parent, child))

    
    for parent, rel, child in triples:
        for noun, cop in toflip:
            if parent == cop: raise Exception("Relation to copula??")
            if parent == noun and rel.id not in KEEP_ON_NOUN_RELIDS: parent = cop
            if child == noun: child = cop
            elif child == cop: child = noun
        yield parent, rel, child
            
            
    

def endTriples(triples):
    """Take the analysis with the highest analysisid (arbitrary)
    If necessary, flip the copula to 'repair' stanford parse"""
    triplesPerAnalysis = {}
    for parent, rel, child, analysisid in triples:
        triplesPerAnalysis[analysisid] =  triplesPerAnalysis.get(analysisid, set()) | set([(parent, rel, child)])
    if not triplesPerAnalysis: return None
    best = max(triplesPerAnalysis.keys())
    triples = triplesPerAnalysis[best]
    if best in NEED_COPULA_FLIP_ANALYSISIDS:
        triples = list(flipCopula(triples))
    return triples

class Sentence(Cachable, graph.Graph):
    __table__ = 'sentences'
    __idcolumn__ = 'sentenceid'
    __labelprop__ = 'text'
    __dbproperties__ = ["parnr", "sentnr", "encoding"]
    __encodingprop__ = 'encoding'
    __metaclass__ = CachingMeta

    text = DBPropertyFactory("isnull(longsentence, sentence)", decode=True)
    article = DBPropertyFactory("articleid", dbfunc=article.doCreateArticle)
    words = DBFKPropertyFactory("parses_words", "wordbegin", objfunc=getSentenceWord, orderby="wordbegin")
    triples = DBFKPropertyFactory("parses_triples", ["parentbegin","relation", "childbegin", "analysisid"], objfunc=getTriple, endfunc=endTriples)
        
    def cacheWords(self, *args, **kargs):
        cacheWords([self], *args, **kargs)
    def getWord(self, position):
        for word in self.words:
            if word.position == position: return word


def cacheWords(sentences, words=True, lemmata=False, triples=False, sentiment=False, sentence=False):
    perword = dict(word = dict(string = []))
    if lemmata: perword["lemma"] = dict(lemma=["string"], pos=[])
    if sentiment: perword["lemma"] = dict(lemma=["string"], pos=[], sentiment=[], intensifier=[])
    what = dict(words={'word' : perword})
    if triples: what["triples"] = []
    cachable.cache(sentences, **what)
    if sentence:
        cachable.cacheMultiple(sentences, "encoding", "text")
        

def computeSentiment(words):
    sum = 0.0
    intens = 1.0
    n = 0
    for word in words:
        lemma = word.word.lemma
        if lemma.sentiment:
            sum += lemma.sentiment
            n += 1
        if lemma.intensifier: intens *= lemma.intensifier
    if not n: return 0.0
    return (sum/n) * intens

def getString(words):
    words = sorted(words, key=lambda w:w.position)
    return " ".join(map(str, words))

class Relation(Cachable):
    __metaclass__ = CachingMeta
    __table__ = "parses_rels"
    __idcolumn__ = "relid"
    __dbproperties__ = ["name"]
    __labelprop__ = 'name'

def cacheRelationNames(db):
    for relid, name in db.doQuery("select relid, name from %s" % Relation.__table__):
        Relation(db, relid, name=name)
    

def getSentence(id):
    return Sentence(dbtoolkit.amcatDB(), id)
    
if __name__ == '__main__':
    db =dbtoolkit.amcatDB(profile=True)
    s = Sentence(db,8202484)
    s.cacheWords(sentiment=True)
    db.printProfile()
    w = list(s.words)
    import random; random.shuffle(w)
    print map(str, w)
    print getString(w)
    
    db.printProfile()
