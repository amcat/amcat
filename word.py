from cachable import Cachable, CachingMeta, DBFKPropertyFactory, DBPropertyFactory
import toolkit, re, dbtoolkit

class BrouwersCat(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'brouwers_cats'
    __idcolumn__ = 'catid'
    __labelprop__ = "cat"
    __dbproperties__ = ["cat", "scat", "sscat"]

class String(Cachable):
    __metaclass__ = CachingMeta
    __table__ = "words_strings"
    __idcolumn__ = "stringid"
    __labelprop__ = "string"
    __dbproperties__ = ["string"]

    def __str__(self): return self.label

class Lemma(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'words_lemmata'
    __idcolumn__ = 'lemmaid'
    __labelprop__ = "lemma"
    __dbproperties__ = ["pos"]
    lemma = DBPropertyFactory("stringid", dbfunc=String)
    brouwers = DBFKPropertyFactory("words_brouwers","cat", dbfunc=BrouwersCat)
    sentiment = DBPropertyFactory("sentiment", table="vw_lemma_sentiment")
    intensifier = DBPropertyFactory("intensifier", table="vw_lemma_sentiment")
    
    def __str__(self): return self.lemma.label

class Word(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'words_words'
    __idcolumn__ = 'wordid'
    __labelprop__ = "word"
    __dbproperties__ = ["freq", "celex"]
    word = DBPropertyFactory("stringid", dbfunc=String)
    lemma = DBPropertyFactory("lemmaid", dbfunc=Lemma)

    def __str__(self): return self.word.label
    
def clean(s):
    if s is None: return ""
    #if type(s) == str:
    #    s = s.decode('latin-1')
    #s = toolkit.stripAccents(s)
    return s.lower().strip()



_WordCreators = {}
def WordCreator(db, language=2):
    return _WordCreator(db, language)
    global _WordCreators
    if language not in _WordCreators:
        _WordCreators[language] = FullyCachedWordCreator(db, language)
    return _WordCreators[language]

        

class BaseWordCreator(object):
    def __init__(self, db, language=2):
        self.db = db
        self.language = language
        self.words, self.lemmata, self.strings, self.pos, self.rels = {}, {}, {}, {}, {}
    def getString(self, string):
        isword = bool(re.match("^[A-Za-z_]+$", string))
        return self.getOrCreate("stringid", self.strings, (clean(string),), "words_strings", ("string",), isword=isword)
    def getLemma(self, string, pos):
        sid = self.getString(string)
        return self.getOrCreate("lemmaid", self.lemmata, (sid,  clean(pos)), "words_lemmata", ("stringid","pos"))
    def getWord(self, string, lemma_or_id, pos=None):
        if type(lemma_or_id) <> int:
            lemma_or_id = self.getLemma(lemma_or_id, pos)
        sid = self.getString(string)
        return self.getOrCreate("wordid", self.words, (lemma_or_id, sid), "words_words", ("lemmaid", "stringid"))
    def getPos(self, major, minor, pos):
        return self.getOrCreate("posid", self.pos, (clean(major), clean(minor), clean(pos)), "parses_pos", ("major","minor","pos"))
    def getRel(self, name):
        return self.getOrCreate("relid", self.rels, (clean(name),), "parses_rels", ("name",))

class CachingWordCreator(BaseWordCreator):
    def getOrCreate(self, idcol, dic, key, table, cols, **extra):
        id = dic.get(key)
        #print "Cache %s : %s from cache: %s" % (table, key, id)
        if id is None:
            sql = "SELECT %s FROM %s WHERE %s" % (idcol, table, " AND ".join("%s=%s" % (k, dbtoolkit.quotesql(v)) for (k,v) in zip(cols, key)))
            #print sql
            id = self.db.getValue(sql)
            #print "GET %s=%s from %s --> %s" % (key, cols, table, id)
            if id is None:
                #print "Inserting"
                data = dict(zip(cols, key))
                data.update(extra)
                id = self.db.insert(table, data)
                #print "PUT %s=%s into %s --> %s" % (key, cols, table, id)
            dic[key] = id
        return id
            
    


class FullyCachedWordCreator(BaseWordCreator):
    def __init__(self, db, language=2):
        BaseWordCreator.__init__(self, db, language)
        self.words = dict(((lid, sid), wid) for (lid, sid, wid) in db.doQuery(
            "SELECT lemmaid, stringid, wordid FROM words_words"))
        self.lemmata = dict(((sid, clean(pos)), lid) for (sid, pos, lid) in db.doQuery(
            "SELECT stringid, pos, lemmaid FROM words_lemmata where languageid=%i" % language))
        self.strings = dict((clean(w), wid) for (w,wid) in db.doQuery(
            "SELECT string, stringid FROM words_strings"))
        self.pos = dict(((clean(maj), clean(min), clean(pos)), pid) for (maj, min, pos, pid) in db.doQuery(
            "SELECT major, minor, pos, posid FROM parses_pos"))
        self.rels = dict((clean(name), relid) for (name, relid) in db.doQuery(
            "SELECT name, relid FROM parses_rels"))
    def getOrCreate(self, idcol, dic, key, table, cols, **extra):
        id = dic.get(key)
        if id is None:
            data = dict(zip(cols, key))
            data.update(extra)
            id = self.db.insert(table, data)
            dic[key] = id
        return id

if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True, easysoft=True)
    #c = WordCreator(db)
    #print c.getPos("punct","komma",".")
    #db.printProfile()
    #db.conn.commit()
    c = CachingWordCreator(db, 2)
    print c.getString("balkenende")

    print c.getWord("balkenende", "balkenende", "M")
    print c.getWord("balkenende", "balkenende", "M")

    print c.getString("balkenende")

    print c.getString("testtesttesttest")

    db.commit()
