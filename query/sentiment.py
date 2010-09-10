import dbtoolkit, toolkit
import project, sentimentdatasource, amcatxapian, sourceinterface,draftdatamodel, article

def sentiment2db(db, articles):
    """
    This method was used to calculate the number of words with positive, negative, and neutral sentiment for each article in the created index, 
    and store it into the sentiment_articles database.
    """
    datamodel = draftdatamodel.getDatamodel(db)
    ###FIXME
    # Shouldn't this point at config['data_index'] instead of a hardcoded path?
    index = amcatxapian.Index("/home/marcel/finaldraftindex", db)
    sent_words = sentimentdatasource.SentimentDataSource(db,datamodel,index)
    words_sentiment = "select lemma, sentiment/100 from parses_lemmas inner join wva.words_sentiment on parses_lemmas.lemmaid=wva.words_sentiment.lemmaid"
    sents = dict(db.doQuery(words_sentiment))
    count = 0
    for a in toolkit.tickerate(articles):
        if type(a) == int: a= article.Article(db, a)
        if db.getValue("select articleid from articles_sentiment where articleid = %i" % a.id):
            continue
        npos, nneg, nneut, nposneg = 0,0,0,0
        articleid = None
        for word in a.words():
            if word in sents.keys():
                if sents[word]==1:
                    npos+=1
                elif sents[word]==-1:
                    nneg+=1
                else:
                    nneut+=1
        count +=1
        if db.getValue("select articleid from articles_sentiment where articleid = %i" % a.id):
            continue
        else:
            #insert new value
            db.insert("articles_sentiment", dict(articleid = a.id, npos = npos, nneg = nneg, nneut = nneut, nposneg = nposneg), retrieveIdent=False)
        db.conn.commit()
        
if __name__ == '__main__':
    db = dbtoolkit.amcatDB()
    articles = []
    arts = db.doQuery("select articles.articleid from articles, storedresults_articles where articles.articleid=storedresults_articles.articleid and storedresults_articles.storedresultid=759")
    for a in arts:
        articles.append(a[0])
    sentiment2db(db, articles)
