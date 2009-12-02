import xapian, dbtoolkit, toolkit
import collections

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
        source = AmcatMetadataField(self, "source", ["articles"], "mediumid")
        url = AmcatMetadataField(self, "url", ["articles"], "url")
        project = AmcatMetadataField(self, "project",["batches"], "projectid")
        return [
          AmcatMetadataMapping(article, batch),
          AmcatMetadataMapping(article, date),
          AmcatMetadataMapping(article, source),
          AmcatMetadataMapping(article, url),
          AmcatMetadataMapping(batch, project),
          ]
    def __str__(self):
        return "Amcat"

class AmcatMetadataField(Field):
    def __init__(self, datasource, concept, tables, column):
        Field.__init__(self, datasource, concept)
        self.tables = tables
        self.column = column

class AmcatMetadataMapping(Mapping):
    def __init__(self, a, b):
        Mapping.__init__(self, a, b)
    def map(self, value, reverse, memo=None):
        if memo is None:
            memo = self.startMapping([value], reverse=reverse)
        return memo[value]

    def startMapping(self, values,reverse):
        tables = set(self.a.tables) & set(self.b.tables)
        if len(tables) <> 1: raise Exception("Intersection not one!")
        table = tables.pop()

        selectcol = self.a.column if reverse else self.b.column
        filtercol = self.b.column if reverse else self.a.column
        values = list(values)

        valuestr = ",".join(map(str, values))
        sql_query = "select %s, %s  from %s where %s in (%s)" % (filtercol,selectcol, table, filtercol, valuestr)

        result_dict = collections.defaultdict(list)
        for k, v in self.a.datasource.db.doQuery(sql_query):
            result_dict[k].append(v)

        return result_dict
    
    def mapmultiple(self, values, reverse):
        tables = set(self.a.tables) & set(self.b.tables)
        if len(tables) <> 1: raise Exception("Intersection not one!")
        table = tables.pop()

        result_dict = dict()
        selectcol = self.a.column if reverse else self.b.column
        filtercol = self.b.column if reverse else self.a.column

        sql_query = "select %s, %s  from %s where %s in (%s)" % (filtercol,selectcol, table, filtercol, toolkit.quotesql(values))
        result_dict = dict(self.a.datasource.db.doQuery(sql_query))

        for k, v in result_dict.iteritems():
            self.map(v, reverse)
        return 
        
if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB()
    ads = AmcatMetadataSource(db)
    
    from mst import getSolution
    from datasource import FunctionalDataModel
    import tabulator
    
    dm = FunctionalDataModel(getSolution)
    dm.register(ads)
    
    filters = { "project" : [368], "article" : [44134082,44135035, 44126401]  }
    select = ["project","article","date", "batch"]

    data = tabulator.tabulate(dm, select, filters)

    print " | ".join(map(lambda x: "%-15s" % x, select))
    print "-+-".join(["-"*15 for x in select])
    for row in data:
        print " | ".join(map(lambda x: "%-15s" % x, row))
