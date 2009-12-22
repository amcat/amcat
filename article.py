import toolkit, dbtoolkit, re, ctokenizer, project, sources
from itertools import izip, count
from functools import partial
_debug = toolkit.Debug('article',1)
from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory

def decode(article, string):
    return dbtoolkit.decode(string, article.encoding)

def createArticle(db, aid, **cache):
    return Article(db, aid, **cache)
import sentence
    
class Article(Cachable):
    """
    Class representing a newspaper article
    """
    __table__ = 'articles'
    __idcolumn__ = 'articleid'
    __labelprop__ = 'headline'
    __dbproperties__ = ["date", "length", "pagenr", "url", "encoding"]
    headline = DBPropertyFactory(objfunc = decode)
    byline = DBPropertyFactory(objfunc = decode)
    metastring = DBPropertyFactory(objfunc = decode)
    section = DBPropertyFactory(objfunc = decode)
    text = DBPropertyFactory(table="texts", objfunc = decode)
    batch = DBPropertyFactory("batchid", dbfunc=lambda db, id: project.Batch(db, id))
    source = DBPropertyFactory("mediumid", dbfunc=sources.Source)
    sentences = DBFKPropertyFactory("sentences", "sentenceid", dbfunc=sentence.Sentence)

    @property
    def fullmeta(self):
        return toolkit.dictFromStr(self.metastring)
    @property
    def project(self):
        return self.batch.project

    def fulltext(self):
        result = (self.headline or '') +"\n\n"+ (self.byline or "")+"\n\n"+(self.text or "")
        return result.replace("\\r","").replace("\r","\n")

    def words(self, onlyWords = False, lemma=0): #lemma: 1=lemmaP, 2=lemma, 3=word
        text = self.text
        if not text: return []
        text = toolkit.stripAccents(text)
        text = text.encode('ascii', 'replace')
        text = ctokenizer.tokenize(text)
        #toolkit.warn("Yielding words for %i : %s" % (self.id, text and len(text) or `text`))
        text = re.sub("\s+", " ", text)
        return text.split(" ")

    def quote(self, words_or_wordfilter, **kargs):
        return toolkit.quote(list(self.words()), words_or_wordfilter, **kargs)


def encodeAndLimitLength(variables, lengths):
    originals = map(lambda x: x and x.strip(), variables)
    numchars = 5
    while True:
        variables, enc = dbtoolkit.encodeTexts(variables)
        done = True
        for i, (var, maxlen, original) in enumerate(zip(variables, lengths, originals)):
            if var and (len(var) > maxlen):
                done = False
                variables[i] = original[:maxlen-numchars] + " ..."
        if done: return variables, enc
        numchars += 5
                
        

def createArticle(db, headline, date, source, batchid, text, texttype=2,
                  length=None, byline=None, section=None, pagenr=None, fullmeta=None, url=None, externalid=None, retrieveArticle=1):
    """
    Writes the article object to the database
    """

    if toolkit.isDate(date): date = toolkit.writeDateTime(date, 1)
    if type(source) == sources.Source: source = source.id
    if type(fullmeta) == dict: fullmeta = `fullmeta`

    if url and len(url) > 490: url = url[:490] + "..."

    (headline, byline, fullmeta, section), encoding = encodeAndLimitLength([headline, byline, fullmeta, section], [740, 999999, 999999, 90])
    
    if pagenr and type(pagenr) in (types.StringTypes): pagenr = pagenr.strip()
    if text: text = text.strip()
    if length == None and text: length = len(text.split())

    
    q = {'date' : date,
         'length' : length,
         'metastring' : fullmeta,
         'headline' : headline,
         'byline' : byline,
         'section' : section,
         'pagenr': pagenr,
         'batchid' : batchid,
         'mediumid' : source,
         'url':url,
         'externalid':externalid,
         'encoding' : encoding}
    aid = db.insert('articles', q)

    text, encoding = dbtoolkit.encodeText(text)
    
    q = {'articleid' : aid,
         'type' : texttype,
         'encoding' : encoding,
         'text' : text}
    
    db.insert('texts', q, retrieveIdent=0)
    
    if retrieveArticle:
        return Article(db, aid)


if __name__ == '__main__':
    import dbtoolkit
    a = Article(dbtoolkit.amcatDB(), 33308863)
    print a.id
    print a.label
    print a.text[:100]
    for s in a.sentences:
        print s.id, s.parnr, s.sentnr, s.label

    
