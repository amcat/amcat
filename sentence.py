import dbtoolkit, toolkit, collections
from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory
from functools import partial
import article, word

class Sentence(Cachable):
    __table__ = 'sentences'
    __idcolumn__ = 'sentenceid'
    __labelprop__ = 'text'
    __dbproperties__ = ["parnr", "sentnr", "encoding"]
    __encodingprop__ = 'encoding'
    
    text = DBPropertyFactory("isnull(longsentence, sentence)", decode=True)
    article = DBPropertyFactory("articleid", dbfunc=article.doCreateArticle)
    words = DBFKPropertyFactory("parses_words", "wordid", dbfunc=word.Word)

    def cacheWords(self, *args, **kargs):
        cacheWords([self], *args, **kargs)

def cacheWords(sentences, words=True, lemmata=False):
    """Cache all the words in the given sentences to avoid many queries
    if words, also cache the word strings
    if lemmata, also cache lemma strings and POS"""
    if type(sentences) == Sentence: sentences = [sentences]
    smap = dict((s.id, s) for s in sentences)
    db = toolkit.head(smap.iteritems())[1].db
        
    SQL = "SELECT sentenceid, w.wordid, w.stringid, w.lemmaid"
    if words: SQL += ", ws.string"
    if lemmata: SQL += ", l.stringid, l.pos, ls.string"
    SQL += " FROM parses_words p inner join words_words w on p.wordid = w.wordid "
    if words: SQL += " INNER JOIN words_strings ws on w.stringid = ws.stringid "
    if lemmata: SQL += (" INNER JOIN words_lemmata l on w.lemmaid = l.lemmaid "
                        +"INNER JOIN words_strings ls on l.stringid = ls.stringid ")
    SQL += " WHERE analysisid=3 and %s" % toolkit.intselectionSQL("sentenceid", smap.keys())
    SQL += " ORDER BY sentenceid, wordbegin"

    cursid, curwords = None, None
    def cache():
        if curwords and cursid: smap[cursid].cacheValues(words=curwords)
    for record in db.doQuery(SQL):
        sid, wid, wsid, lid = record[:4]
        if  lemmata:
            lsid, pos, lstr = record[-3:]
        if words: wstr = record[4]

        if sid <> cursid:
            cache()
            cursid, curwords = sid, []

        ws = word.String(db, wsid)
        if words: ws.cacheValues(string=wstr)
        l = word.Lemma(db, lid)
        if lemmata:
            ls = word.String(db, lsid)
            ls.cacheValues(string=lstr)
            l.cacheValues(pos=pos, lemma=ls)
            
        w = word.Word(db, wid)
        w.cacheValues(word=ws, lemma=l)
        curwords.append(w)
    cache()

        
    
if __name__ == '__main__':
    db =dbtoolkit.amcatDB(profile=True)
    s = Sentence(db,30031005)
    s.cacheWords(words=True, lemmata=True)
    #print " ".join("%s" % w for w in s.words)
    print " ".join("%s/%s" % (w.lemma, w.lemma.pos) for w in s.words)
    #print s.__properties__
    db.printProfile()
