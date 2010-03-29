import xapian, amcatxapian, dbtoolkit, toolkit
from datasource import DataSource, Mapping, Field
from itertools import imap, izip
from amcatxapian import Index
import article

class SearchDataSource(DataSource):
    """
    datamodel:= draft datamodel
    indx:=index of the articles for draft
    Returns a mapping of search to articles, to find articles in which searchterms are mentioned
    """
    def __init__(self, datamodel,indx):
        DataSource.__init__(self, self.createMappings(datamodel))
        self.index = indx
    def createMappings(self, dm):
        article = Field(self, dm.getConcept("article") )
        searchterm = Field(self, dm.getConcept("search"))
        return [
            SearchDataMapping(searchterm, article)
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
        inx = self.a.datasource.index
        document = inx.getDocument(value)
        for term in document.termlist():
            yield term[0]
                    
    def getArtikelenPerSearchterm(self,value):
        terms = [x.lower() for x in value.split()]
        query = xapian.Query(xapian.Query.OP_AND, terms)
        index = self.a.datasource.index.query(query)
        for art in index:
            yield art
            
if __name__ == '__main__':
    import dbtoolkit, tabulator
    from sourceinterface import *
    db = dbtoolkit.amcatDB()
    p = 368
    filters = {"search": (u'heineken',)}
    #filters = {'article':(44142110,)}
    data = getList(db,["search"], filters)
    print data.data
       
