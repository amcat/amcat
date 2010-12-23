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

import xapian, amcatxapian, dbtoolkit, toolkit
from datasource import DataSource, Mapping, Field
from itertools import imap, izip
from amcatxapian import Index
import article
from amcatmetadatasource import ConceptMapper, MappedField

class SearchDataSource(DataSource):
    """
    datamodel:= draft datamodel
    indx:=index of the articles for draft
    Returns a mapping of search to articles, to find articles in which searchterms are mentioned
    """
    def __init__(self, datamodel,indx, db):
        DataSource.__init__(self, self.createMappings(datamodel, db))
        self.index = indx
    def createMappings(self, dm, db):
        artfield = MappedField(self, dm.getConcept("article"), ConceptMapper(db, article.Article))
        searchterm = Field(self, dm.getConcept("search"))
        return [
            SearchDataMapping(searchterm, artfield)
            ]
    def __str__(self):
        return "Search"

class SearchDataMapping(Mapping):
    def __init__(self, a, b):
        Mapping.__init__(self, a, b, 1, 99999)
    def map(self, value, reverse, memo=None):
        if reverse:
            return self.getTermsPerArticle(value)
        else:
            return self.getArtikelenPerSearchterm(value)

    def getTermsPerArticle(self,value):
        for term in self.a.datasource.index.getTerms(value):
            yield term

    def getArtikelenPerSearchterm(self,value):
        for aid in self.a.datasource.index.searchOnTerm(value):
            yield aid

if __name__ == '__main__':
    import dbtoolkit, tabulator
    from sourceinterface import *
    db = dbtoolkit.amcatDB()
    p = 368
    filters = {"search": (u'heineken',)}
    #filters = {'article':(44142110,)}
    data = getList(db,["search"], filters)
    print data.data
       
