import xapian, amcatxapian, dbtoolkit, toolkit
from datasource import DataSource, Mapping, Field
from itertools import imap, izip

class MerkDataSource(DataSource):
    def __init__(self, db,indx):
        DataSource.__init__(self,self.createMappings())
        self.db = db
        #self.brand = brand
        self.index = indx
        self.brands = ["dsb", "yakult", "melkunie"]  
    def createMappings(self):
        article = Field(self, "article")
        merk = Field(self, "merk")
        return [
            MerkDataMapping(merk, article)
            ]


class MerkDataMapping(Mapping):
    def __init__(self, a, b):
        Mapping.__init__(self, a, b)
    def map(self, value, reverse):
        #print a,b
        if reverse:
            return self.getMerkenPerArticle(value)
        else:
            return self.getArtikelenPerMerk(value)
        
    def getMerkenPerArticle(self,value):
        index = self.a.datasource.index
        brands = self.a.datasource.brands
        for brand in brands:
            art = index.query(brand)
            for ar in art:
                if value == str(ar.id):
                    yield brand
    def getArtikelenPerMerk(self,value):
        index = self.a.datasource.index.query(value)
        for i in index:
            yield i
        

if __name__ == '__main__':
    import dbtoolkit, sys
    db = dbtoolkit.amcatDB()
      
    from mst import getSolution
    from datasource import FunctionalDataModel
    import tabulator
    #filters = {"merk" : ["yakult"] }
    filters = {"article": ["44134035"]}
    select = ["article", "merk"]
    index =  amcatxapian.Index("/home/marcel/amcatindex", dbtoolkit.amcatDB())
    merk = MerkDataSource(db,index)
    dm = FunctionalDataModel(getSolution)
    dm.register(merk)
    data = tabulator.tabulate(dm,select,filters)
    print data
