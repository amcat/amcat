from datasource import DataSource, Mapping, Field
from amcatmetadatasource import DatabaseField, ConceptMapper, DatabaseMapping
import article

class SentimentDataSource(DataSource):
    """ 
    Creates a mapping of articles to sentiment.
    db := dbtoolkit.amcatDB (or raw connection)
    datamodel := datamodel from which to get the concepts and create the fields for the mapping
    indx := The index in which to perform the query
    """
    def __init__(self, db, datamodel):
        self.db = db
        DataSource.__init__(self, self.createMappings(datamodel))
        
    def createMappings(self,datamodel):
        art = DatabaseField(self, datamodel.getConcept("article"), ["articles", "vw_all_articles_sentiment"], "articleid", ConceptMapper(self.db, article.Article))
        sentiment = DatabaseField(self, datamodel.getConcept("sentiment"), ["vw_all_articles_sentiment"], "sentiment")
        return [
            DatabaseMapping(art, sentiment)
            ]
 
