from cachable import *
import toolkit

class BrouwersCat(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'brouwers_cats'
    __idcolumn__ = 'catid'
    __labelprop__ = "cat"
    __dbproperties__ = ["cat", "scat", "sscat"]

class Lemma(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'words_lemmata'
    __idcolumn__ = 'lemmaid'
    __labelprop__ = "lemma"
    __dbproperties__ = ["lemma", "pos"]
    brouwers = DBFKPropertyFactory("words_brouwers","cat", dbfunc=BrouwersCat)
    

class Word(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'words_words'
    __idcolumn__ = 'wordid'
    __labelprop__ = "word"
    __dbproperties__ = ["word", "freq", "celex"]
    lemma = DBPropertyFactory("lemmaid", dbfunc=Lemma)

def clean(s):
    if s is None: return ""
    if type(s) == str:
        s = s.decode('latin-1')
    #s = toolkit.stripAccents(s)
    return s.lower().strip()

class RelCache(object):
    def __init__(self, db):
        self.db = db
        SQL = "select name, relid from parses_rels"
        self.rels = dict(db.doQuery(SQL))
    def getRelID(self, rel):
        return self.rels[rel]

class LemmaCache(object):
    def __init__(self, db, languageid=2):
        self.db = db
        SQL = "select lemmaid, lemma, pos from words_lemmata"# where languageid=%i" % languageid
        self.words = {}
        self.languageid = languageid
        for lid, lemma, pos in db.doQuery(SQL):
            lemma, pos = clean(lemma), clean(pos)
            self.words[lemma, pos] = lid
    def getLemmaID(self, lemma, pos, create=False):
        lemma2, pos2 = clean(lemma), clean(pos)
        lid = self.words.get((lemma2, pos2))
        if not lid and create:
            lid = self.db.insert("words_lemmata", dict(lemma=lemma, pos=pos, languageid=self.languageid))
            self.words[lemma2, pos2] = lid
        return lid

    
class WordLemmaCache(object):
    def __init__(self, db):
        self.db = db
        SQL = "select wordid, lemmaid, word from words_words"
        self.words = {}
        for wid, lid, word in db.doQuery(SQL):
            word = clean(word)
            self.words[lid, word] = wid
    def getWordID(self, lid, word, create=False):
        word2 = clean(word)
        wid = self.words.get((lid, word2))
        if not wid and create:
            wid = self.db.insert("words_words", dict(word=word, lemmaid=lid))
            self.words[lid, word2] = wid
        return wid
        
    
class WordCache(object):
    def __init__(self, db):
        self.db = db
        SQL = "select word, wordid from words_words"
        self.words = collections.defaultdict(list)
        for word, wordid in self.db.doQuery(SQL):
            self.words[word].append(wordid)
    def lookup(self, word):
        return [Word(db, wid) for wid in self.words[word]]
    def getLemmata(self, word):
        return set(Word(self.db, wid).lemma for wid in self.words[word])
    def getBrouwersCats(self, word, prop=None):
        result = set()
        for lemma in self.getLemmata(word):
            for b in lemma.brouwers:
                if prop:
                    result.add(b.__getattribute__(prop))
                else:
                    result.add(b)
        return result

class POSCache(object):
    def __init__(self, db):
        self.db = db
        SQL= "select posid, major, minor, pos from parses_pos"
        self.poss = {}
        for posid, major, minor, pos in db.doQuery(SQL):
            major, minor, pos = clean(major), clean(minor), clean(pos)
            self.poss[major, minor, pos] = posid
    def getPosID(self, major, minor, pos, create=False):
        major2, minor2, pos2 = clean(major), clean(minor), clean(pos)
        posid = self.poss.get((major2, minor2, pos2))
        if not posid and create:
            posid = self.db.insert("parses_pos", dict(major=major, minor=minor, pos=pos))
            self.poss[major2, minor2, pos2] = posid
        return posid

if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True)
    print LemmaCache(db).getLemmaID(":", ".")
