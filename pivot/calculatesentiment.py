import datasource

class ArticleSentiment(o):
    import dbtoolkit
    import amcatxapian, xapian, aggregator
    
    def __init__(self, index,db, merk):
        self.index = index
        self.db = db
        self.articles = self.index.query(merk)

    def calculateSentimentArticle(self, article):
        docid = self.index.getDocumentID(article)
        words_sentiment = "select lemma, sentiment/100 from words_lemmata l inner join wva.words_sentiment s on l.lemmaid = s.lemmaid"
        sdict = dict(self.db.doQuery(words_sentiment))
        print sdict
        return
        sumsentiment=0
        for lemma, lemmaid, sentiment in sentiments:
            if not lemma:
                print lemma
                break
            if lemma in article.getText():
                sumsentiment+=int(sentiment)
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
    for a in artsent.calculateSentiments():
        print a

## class ArticleAggregateFunction(AggregateFunction):
##     def __init__(self, article):
##         AggregateFunction.__init__(self, article)
##         self.total = 0
##     def running(self, value):
##         return self.total + value
##     def final(self):
##         return self.total
