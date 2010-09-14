def doCreateArticle(db, aid, **cache):
    return Article(db, aid, **cache)
def doCreateSentence(db, aid, **cache):
    import sentence
    return sentence.Sentence(db, aid, **cache)

import toolkit, dbtoolkit, re, project, sources, types, quote
from itertools import izip, count
from functools import partial
_debug = toolkit.Debug('article',1)
from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory, CachingMeta, cacheMultiple


    
class Article(Cachable):
    """
    Class representing a newspaper article
    """
    __table__ = 'articles'
    __idcolumn__ = 'articleid'
    __labelprop__ = 'headline'
    __encodingprop__ = 'encoding'
    __dbproperties__ = ["date", "length", "pagenr", "url", "encoding"]
    __metaclass__ = CachingMeta
    headline = DBPropertyFactory(decode=True)
    byline = DBPropertyFactory(decode=True)
    metastring = DBPropertyFactory(decode=True)
    section = DBPropertyFactory(decode=True)
    batch = DBPropertyFactory("batchid", dbfunc=lambda db, id: project.Batch(db, id))
    source = DBPropertyFactory("mediumid", dbfunc=sources.Source)
    sentences = DBFKPropertyFactory("sentences", "sentenceid", dbfunc=doCreateSentence)
    
    @property
    def text(self):
        return(self.db.getText(self.id))

    @property
    def fullmeta(self):
        return toolkit.dictFromStr(self.metastring)
    @property
    def project(self):
        return self.batch.project

    def fulltext(self):
        result = (self.headline or '') +"\n\n"+ (self.byline or "")+"\n\n"+(self.text or "")
        return result.replace("\\r","").replace("\r","\n")

    def getArticle(self):
        "Convenience function also present in CodedArticle, CodedUnit"
        return self

    def words(self, onlyWords = False, lemma=0, headline=False): #lemma: 1=lemmaP, 2=lemma, 3=word
        import ctokenizer
        text = self.text
        if headline and self.headline: text = self.headline + "\n\n" + text
        if not text: return []
        text = toolkit.stripAccents(text)
        text = text.encode('ascii', 'replace')
        text = ctokenizer.tokenize(text)
        #toolkit.warn("Yielding words for %i : %s" % (self.id, text and len(text) or `text`))
        text = re.sub("\s+", " ", text)
        return text.split(" ")

    def quote(self, words_or_wordfilter, **kargs):
        return quote.quote(list(self.words(headline = True)), words_or_wordfilter, **kargs)
    
    def getSentence(self, parnr, sentnr):
        for s in self.sentences:
            if s.parnr == parnr and s.sentnr == sentnr:
                return s

def Articles(aids, db):
    if db is None: raise Exception("Need a db connection to create articles")
    arts = [Article(db, aid) for aid in aids]
    if any(a.db is None for a in arts): raise Exception("Article has no db??")
    return arts

def cacheText(articles):
    cacheMultiple(articles, "encoding", "headline", "text")

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

if __name__ == '__main__':
    import dbtoolkit
    a = Article(dbtoolkit.amcatDB(), 33308863)
    print a.quote(["de"])
