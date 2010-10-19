###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
Object-layer module containing classes modelling sentences
"""

import dbtoolkit, toolkit, collections
from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory,ForeignKey, CachingMeta
import cachable
from functools import partial
import article, word
import graph

class SentenceWord(graph.Node, Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'parses_words'
    __idcolumn__ = ['sentenceid','analysisid','wordbegin']
    __labelprop__ = 'word'
    word = DBPropertyFactory("wordid", dbfunc=word.Word)
    def __init__(self, *args, **kargs):
        Cachable.__init__(self, *args, **kargs)
        graph.Node.__init__(self)
    @property
    def sentence(self):
        return Sentence(self.db, self.id[0])
    @property
    def analysedSentence(self):
        return AnalysedSentence(self.db, self.id[:2])
    def getGraph(self):
        return self.analysedSentence

    def __str__(self):
        return "%i:%s" % (self.position, self.word)
    
    @property
    def position(self):
        return self.id[2]
    def getNeighbour(self, offset=1):
        return self.sentence.getWord(self.position + offset)

def getAnalysedSentence(sentence, analysisid):
    return AnalysedSentence(sentence.db, sentence.id, analysisid)
    
class Sentence(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'sentences'
    __idcolumn__ = 'sentenceid'
    __labelprop__ = 'text'
    __dbproperties__ = ["parnr", "sentnr", "encoding"]
    __encodingprop__ = 'encoding'

    text = DBPropertyFactory("isnull(longsentence, sentence)", decode=True)
    article = DBPropertyFactory("articleid", dbfunc=article.doCreateArticle)
    analysedSentences = DBFKPropertyFactory("parses_words", "analysisid", objfunc=getAnalysedSentence, distinct=True)
        
    def cacheWords(self, *args, **kargs):
        cacheWords([self], *args, **kargs)
        
    def getAnalysedSentence(self, analysisid):
        for a in self.analysedSentences:
            if analysisid == a.analysisid:
                return a

def getSentenceWord(analysedSentence, position):
    return SentenceWord(analysedSentence.db, (analysedSentence.sentenceid, analysedSentence.analysisid, position))


def getTriple(sent, parent, rel, child):
    parent, child = map(sent.getWord, (parent, child))
    rel = Relation(sent.db, rel)
    return parent, rel, child
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
    triples = list(triples)
    if triples:
        anid = triples[0][0].analysedSentence.analysisid
    if anid in NEED_COPULA_FLIP_ANALYSISIDS:
        triples = list(flipCopula(triples))
    return triples

class AnalysedSentence(Cachable, graph.Graph):
    __metaclass__ = CachingMeta
    __idcolumn__ = ('sentenceid', 'analysisid')
    triples = DBFKPropertyFactory("parses_triples", ["parentbegin","relation", "childbegin"], objfunc=getTriple, endfunc=endTriples)
    words = DBFKPropertyFactory("parses_words", "wordbegin", objfunc=getSentenceWord, orderby="wordbegin")

    #analysis = DBPropertyFactory("analysisid", factory=Sentence)
    def __init__(self, db, id_or_sentenceid, analysisid=None):
        if analysisid:
            idtuple = (id_or_sentenceid, analysisid)
        else:
            idtuple = id_or_sentenceid
        self.sentenceid, self.analysisid = idtuple
        Cachable.__init__(self, db, idtuple)
    def getWord(self, position):
        for word in self.words:
            if word.position == position: return word


def cacheWords(sentences, words=True, lemmata=False, triples=False, sentiment=False, sentence=False):
    perword = dict(word = dict(string = []))
    if lemmata: perword["lemma"] = dict(lemma=["string"], pos=[])
    if sentiment: perword["lemma"] = dict(lemma=["string"], pos=[], sentiment=[], intensifier=[])
    what = dict(analysedSentences = dict(words={'word' : perword}))
    if triples: what["analysedSentences"] = ["triples"]
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
