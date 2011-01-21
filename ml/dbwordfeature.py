import collections, math
from amcat.model import article
from amcat.model.coding import codedarticle, codedsentence
from amcat.tools import toolkit
import re

PRINTFEATURES = False

def tf(tf, d, df):
    return tf
def logtfidf(tf, d, df):
    s = math.log(tf + .5) * math.log(d / float(df))
    #print "log(tf).log(idf) = log(%i + .5) * log(%i / %i) = %1.3f" % (tf, d, df, s)
    return s
def tfidf(tf, d, df):
    s = tf * math.log(d / float(df))
    #print "tf.log(idf) = %i * log(%i / %i) = %1.3f" % (tf, d, df, s)
    return s

TRANS = "SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED\n "

VW_LEMMA = "wva.vw_lemmafreqs"
VW_WORD = "wva.vw_wordfreqs"
VW_LEMMASTRING = "wva.vw_lemmastringfreqs"
VW_WORDSTRING = "wva.vw_wordstringfreqs"

def getFeatures(db, corpusclause, view, fthres=1, dfthres=None):
    docfreqs = {}
    SQL = TRANS+"select id, sum(n), count(distinct articleid) from %s where articleid in (%s) and analysisid=3 group by id having sum(n) >= %i" % (view, corpusclause, fthres)
    for id, n, ndocs in db.doQuery(SQL, select=True):
        if 'raw' in view:
            if not re.match("[A-Za-z]+", id): continue
        docfreqs[id] = ndocs
    SQL = TRANS+"select count(distinct articleid) from %s where articleid in (%s) and analysisid=3 " % (view, corpusclause)
    ndocs = db.getValue(SQL)
    if dfthres:
        dels = set()
        dfthres = int(ndocs * dfthres)
        for id, df in docfreqs.iteritems():
            if df > dfthres:
                dels.add(id)
        for id in dels:
            del docfreqs[id]
    features = {}
    for id in docfreqs:
        features[id] = len(features)+1
    #return docfreqs, features, ndocs
    return features

class DBWordFeatureSet(object):
    def __init__(self, db, view, features):
        self.db = db
        self.view = view
        self.features =features

    def start(self, units):
        self.memo = collections.defaultdict(list)

        for subset in toolkit.splitlist(units, 1000):
            aidsel = self.db.intSelectionSQL("articleid", map(getAID, subset))
            idsel = ""
            #idsel = "AND (%s)" % toolkit.intselectionSQL("id", self.lid2fno.keys())
            SQL = "select articleid, id, sum(n) from %s where analysisid=3 and (%s) %s group by articleid, id" % (self.view, aidsel, idsel)
            for aid, id, n in self.db.doQuery(SQL):
                if id in self.features:
                    self.memo[aid].append((id, self.getScore(id, n)))
    
    def getScores(self, unit):
        aid = getAID(unit)
        scores = {}
        for id, s in self.memo[aid]:
            scores[self.features[id]] = s
        return sorted(scores.items())

    def getScore(self, id, n):
        if PRINTFEATURES: print id, n
        return n
        #return self.weight(n, self.ndocs, self.docfreqs[id])
    
    def getDict(self, unit):
        return dict(self.getScores(unit))
    
def getAID(unit):
    if type(unit) == int:
        return unit
    if type(unit) == article.Article:
        return unit.id
    if type(unit) == codedarticle.CodedArticle:
        return unit.article.id
    if type(unit) == codedsentence.CodedSentence:
        return unit.ca.article.id
    
    raise Exception("Help! %s" % type(unit))

if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB()
    aids = 42445289,42445290,42445291,42445292,42445293,42445294,42445295,42445296,42445297,42445298
    where = ",".join(map(str, aids))
    #where = "select articleid from articles where batchid=5309"
    
    features = getFeatures(db, where, VW_WORDSTRING, 1)
    s = DBWordFeatureSet(db, VW_WORDSTRING, features)
    print s.features
    
