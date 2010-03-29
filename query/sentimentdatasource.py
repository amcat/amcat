import xapian, amcatxapian, dbtoolkit, toolkit, article, amcatmetadatasource
from datasource import DataSource, Mapping, Field

class SentimentDataSource(DataSource):
    """ 
    Creates a mapping of articles to sentiment.
    db := dbtoolkit.amcatDB (or raw connection)
    datamodel := datamodel from which to get the concepts and create the fields for the mapping
    indx := The index in which to perform the query
    """
    def __init__(self, db,datamodel, indx):
        DataSource.__init__(self, self.createMappings(datamodel))
        self.db = db
        self.index = indx
        #words_sentiment = "select lemma, sentiment/100 from words_lemmata l inner join wva.words_sentiment s on l.lemmaid = s.lemmaid"
        self._sentiments = None
        
    def createMappings(self,dm):
        """ 
        dm := datamodel
        Returns a mapping of the sentiment to the article
        """
        article = Field(self, dm.getConcept("article"))
        sentiment = Field(self, dm.getConcept("sentiment"))
        return [
            SentimentDataMapping(sentiment, article)
            ]

    @property
    def sentiments(self):
        if self._sentiments is None:
            self._sentiments = {}
            for aid, pos, neg in self.db.doQuery("select articleid, npos, nneg from articles_sentiment"):
                self.sentiments[aid] = pos - neg
        return self._sentiments
    
class SentimentDataMapping(Mapping):

    def __init__(self, a, b):
        Mapping.__init__(self, a, b)

    def map(self, value, reverse, memo=None):
        """ 
        Find the values for the mapping to 'value '
        """
        if reverse:
            return self.getSentimentPerArticle(value)
        else:
            return self.getArtikelenPerSentiment(value)

    def getSentimentPerArticle(self, art):
        sentiments = self.a.datasource.sentiments
        return (sentiments.get(art.id, 0),)
    
    def getArtikelenPerSentiment(self, value):
        index = self.a.datasource.index.query(value)
        for art in index:
            yield art

if __name__ == '__main__':
    import dbtoolkit, sys
    db = dbtoolkit.amcatDB()

    from mst import getSolution
    from datasource import FunctionalDataModel
    import tabulator

    index = amcatxapian.Index("/home/marcel/amcatindex", dbtoolkit.amcatDB())
    dm = FunctionalDataModel(getSolution)
    sentiment = SentimentDataSource(db, dm,index)
    article = amcatmetadatasource.AmcatMetadataSource(db, dm)
    dm.register(sentiment)
    dm.register(article)
    art = dm.getConcept("article")
    sent = dm.getConcept("sentiment")
    filters = {art: [44133948]}
    select = [art, sent]
    data = tabulator.tabulate(dm, select, filters)
    print data
