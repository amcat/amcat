import xapian, amcatxapian, dbtoolkit, toolkit
from datasource import DataSource, Mapping, Field

class SentimentDataSource(DataSource):
    def __init__(self, db, indx):
        DataSource.__init__(self, self.createMappings())
        self.db = db
        self.index = indx
        self.sentiments = ["gezond", "beheerst", "flexibel", "ziek"]

    def createMappings(self):
        article = Field(self, "article")
        sentiment = Field(self, "sentiment")
        return [
            SentimentDataMapping(sentiment, article)
            ]

class SentimentDataMapping(Mapping):
    def __init__(self, a, b):
        Mapping.__init__(self, a, b)

    def map(self, value, reverse):
        if reverse:
            return self.getSentimentPerArticle(value)
        else:
            return self.getArtikelenPerSentiment(value)

    def getSentimentPerArticle(self, value):
        index = self.a.datasource.index
        sentiments = self.a.datasource.sentiments

        for sentiment in sentiments:
            sent_arts = index.query(sentiment)
            for sa in sent_arts:
                if value == str(sa.id):
                    yield sentiment
    
    def getArtikelenPerSentiment(self, value):
        index = self.a.datasource.index.query(value)
        for i in index:
            yield i

if __name__ == '__main__':
    import dbtoolkit, sys
    db = dbtoolkit.amcatDB()

    from mst import getSolution
    from datasource import FunctionalDataModel
    import tabulator

    filters = {"article": ["44133948"]}
    select = ["article", "sentiment"]
    index = amcatxapian.Index("/home/marcel/amcatindex", dbtoolkit.amcatDB())
    sentiment = SentimentDataSource(db, index)
    dm = FunctionalDataModel(getSolution)
    dm.register(sentiment)
    data = tabulator.tabulate(dm, select, filters)
    print data
