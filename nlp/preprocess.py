from itertools import izip, count
import sbd, re, dbtoolkit, toolkit
import tadpole
import alpino, lemmata
import sys, traceback



def splitArticle(art):
    if not art.db: raise Exception("Article %r has no db!" % art)
    if art.sentences: return
    text = art.db.getText(art.id)
    if not text:
        toolkit.warn("Article %s empty, adding headline only" % art.id)
        text = ""                                                                                                             
    text = re.sub(r"q11\s*\n", "\n\n",text)                                                                                   
    #if article.byline: text = article.byline + "\n\n" + text                                                                 
    if art.headline: text = art.headline.replace(";",".")+ "\n\n" + text                                              
    spl = sbd.splitPars(text,  maxsentlength=2000, abbreviateIfTooLong=True)                                                                                                 
    for parnr, par in izip(count(1), spl):                                                                                    
        for sentnr, sent in izip(count(1), par):                                                                              
            sent = sent.strip()                                                                                               
            orig = sent                                                                                                       
            [sent], encoding = dbtoolkit.encodeTexts([sent])                                                                  
            if len(sent) > 6000:
                raise Exception("Sentence longer than 6000 characters, this is not normal!")
            art.db.insert("sentences", {"articleid":art.id, "parnr" : parnr, "sentnr" : sentnr, "sentence" : sent, 'encoding': encoding})
    art.removeCached("sentences")
    
def splitArticles(articles):                                                                                            
    error = ''
    for article in articles:
        try:
            splitArticle(article)
            article.db.commit()
        except Exception, e:
            error += '%s: %s\n' % (article.id , e)    
            error += ''.join(traceback.format_exception(*sys.exc_info()))
    return error or None

def parseArticles(articles):
    if type(articles) not in (tuple, list, set): articles = set(articles)
    db = toolkit.head(articles).db
    toolkit.ticker.warn("Splitting articles")
    splitArticles(articles)
    toolkit.ticker.warn("SEtting up lemmatiser")
    lem = lemmata.Lemmata(db, alpino.ALPINO_ANALYSISID)
    for article in toolkit.tickerate(articles, msg="Parsing", detail=1):
        for sent in article.sentences:
            alpino.parseAndStoreSentence(lem, sent)
        article.db.commit()

if __name__ == '__main__':
    import dbtoolkit, article
    db  = dbtoolkit.amcatDB()
    aids = 44721769,46056991
    arts = [article.Article(db, aid) for aid in aids]
    #parseArticles(arts)
    splitArticles(arts)
#a = article.Article(db, 634584)
    #print a.sentences


