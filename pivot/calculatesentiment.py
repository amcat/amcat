

class ArticleSentiment(object):
    import dbtoolkit
    import amcatxapian, xapian, aggregator
    
    def __init__(self, index,db, merk):
        self.index = index
        self.db = db
        self.articles = self.index.query(merk)

    def calculateSentimentArticle(self, article):
        docid = self.index.getDocumentID(article)
        words_sentiment = "select lemma, lemmaid, sentiment from words_lemmata, words_sentiment where words_sentiment.lemmaid = words_lemmata.lemmaid"
        #words_sentiment = "select lemmaid from words_lemmata"
        sentiments = self.db.doQuery(words_sentiment)
        #print sentiments
        sumsentiment=0
        for lemma in sentiments[2]:
            sumsentiment+=int(lemma)

        return sumsentiment
    
    def calculateSentiments(self):
        totaalsentiment = 0
        for art in self.articles:
            print type(art)
            sentiment = self.calculateSentimentArticle(art)
            totaalsentiment += sentiment
            yield art.id, sentiment

    def calculateTotaalSentimentBrand(self):
        totaal = calculateSentiments()
        somtotaal = 0
        for aid, sentiment in totaal:
            somtotaal += sentiment
        return self.merk, somtotaal

if __name__ == '__main__':
    import amcatxapian, xapian, dbtoolkit

    i = amcatxapian.Index("/home/marcel/amcatindex",dbtoolkit.amcatDB())
    db = dbtoolkit.amcatDB()
    artsent = ArticleSentiment(i, db, "yakult")
    print artsent.calculateSentiments()

## class ArticleAggregateFunction(AggregateFunction):
##     def __init__(self, article):
##         AggregateFunction.__init__(self, article)
##         self.total = 0
##     def running(self, value):
##         return self.total + value
##     def final(self):
##         return self.total
