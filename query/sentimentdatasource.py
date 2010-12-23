###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

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
 
