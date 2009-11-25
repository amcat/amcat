import xapian, dbtoolkit, toolkit

from datasource import DataSource, Mapping, Field
from itertools import imap, izip

class AmcatMetadataSource(DataSource):
    def __init__(self, db):
        DataSource.__init__(self, self.createMappings())
        self.db = db
    def createMappings(self):
        article = AmcatMetadataField(self, "article", ["articles"], "articleid")
        batch = AmcatMetadataField(self, "batch", ["articles", "batches"], "batchid")
        date = AmcatMetadataField(self, "date", ["articles"], "date")
        source = AmcatMetadataField(self, "source", ["articles"], "url")
        project = AmcatMetadataField(self, "project",["batches"], "projectid")
        return [
          AmcatMetadataMapping(article, batch),
          AmcatMetadataMapping(article, date),
          AmcatMetadataMapping(article, source),
          AmcatMetadataMapping(batch, project),
          ]

class AmcatMetadataField(Field):
    def __init__(self, datasource, concept, tables, column):
        Field.__init__(self, datasource, concept)
        self.tables = tables
        self.column = column

class AmcatMetadataMapping(Mapping):
    def __init__(self, a, b):
        Mapping.__init__(self, a, b)
    def map(self, value, reverse):
        # determine table
        tables = set(self.a.tables) & set(self.b.tables)
        if len(tables) <> 1: raise Exception("Intersection not one!")
        table = tables.pop()
        # construct sql
        selectcol = self.a.column if reverse else self.b.column
        filtercol = self.b.column if reverse else self.a.column
        
        sql = "select %s from %s where %s=%s" % (
            selectcol, table, filtercol, toolkit.quotesql(value))
        #print self.a.datasource.db.doQuery(sql)
        return (x[0] for x in self.a.datasource.db.doQuery(sql))
    
    def xxmapmultiple(self, values, reverse):
        # determine table
        tables = set(self.a.tables) & set(self.b.tables)
        if len(tables) <> 1: raise Exception("Intersection not one!")  
        table = tables.pop()
        # construct sql
        selectcol = self.a.column if reverse else self.b.column
        filtercol = self.b.column if reverse else self.a.column
        valstr = ",".join(imap(toolkit.quotesql, values))

        sql = "select %s, %s from %s where %s in (%s)"% (filtercol, selectcol, table,filtercol,valstr)
        print sql

        import sys; sys.exit()
        #sql = "select %s from %s where"% (selectcol, table)

        #for value in values:
            #sql = sql + " %s=%s OR" % (filtercol, toolkit.quotesql(value[0]))

        #minOR = len(" OR")
        #sql = sql[0:len(sql)-minOR]
        print self.a.datasource.db.doQuery(sql)
        
        # more efficient implementation
        return (x[0] for x in self.a.datasource.db.doQuery(sql))
    
if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB()
    ads = AmcatMetadataSource(db)
    
    from mst import getSolution
    from datasource import FunctionalDataModel
    import tabulator
    
    dm = FunctionalDataModel(getSolution)
    dm.register(ads)
    
    filters = { "project" : [368], "article" : [44126388, 44126404, 44126401]  }
    select = ["project","article", "date", "batch"]

    data = tabulator.tabulate(dm, select, filters)

    print " | ".join(map(lambda x: "%-15s" % x, select))
    print "-+-".join(["-"*15 for x in select])
    for row in data:
        print " | ".join(map(lambda x: "%-15s" % x, row))
