import xapian, dbtoolkit, toolkit
import collections

from datasource import DataSource, Mapping, Field
from itertools import imap, izip

WEEKSQL = "cast(datepart(year, date) as varchar) + '/' + REPLICATE(0,2-LEN(cast(datepart(week, date) as varchar)))+ CONVERT(VARCHAR,cast(datepart(week, date) as varchar))"
DATESQL = "convert(varchar(10), date, 102)"
DATESQL = "convert(int, convert(varchar(10), date, 112)) "
WEEKSQL = "datepart(year,date) * 100 + datepart(week, date)"
YEARSQL = "datepart(year, date)"

class AmcatMetadataSource(DataSource):
    def __init__(self, db, datamodel):
        DataSource.__init__(self, self.createMappings(datamodel))
        self.db = db
    def createMappings(self, datamodel):
        article = AmcatMetadataField(self, datamodel.getConcept("article"), ["articles"], "articleid")
        batch = AmcatMetadataField(self, datamodel.getConcept("batch"), ["articles", "batches"], "batchid")
        headline = AmcatMetadataField(self, datamodel.getConcept("headline"), ["articles"], "headline")
        quote = AmcatMetadataField(self, datamodel.getConcept("quote"), ["articles"], "headline")
        date = AmcatMetadataField(self, datamodel.getConcept("date"), ["articles"], DATESQL)
        week = AmcatMetadataField(self, datamodel.getConcept("week"), ["articles"], WEEKSQL)
        year = AmcatMetadataField(self, datamodel.getConcept("year"), ["articles"], YEARSQL)
        source = AmcatMetadataField(self, datamodel.getConcept("source"), ["articles","media"], "mediumid")
        url = AmcatMetadataField(self, datamodel.getConcept("url"), ["articles"], "url")
        project = AmcatMetadataField(self, datamodel.getConcept("project"),["batches"], "projectid")
        sourcetype = AmcatMetadataField(self, datamodel.getConcept("sourcetype"),["media"], "type")
        return [
          AmcatMetadataMapping(article, batch),
          AmcatMetadataMapping(article, date),
          AmcatMetadataMapping(article, week),
          AmcatMetadataMapping(article, year, 1000),
          AmcatMetadataMapping(article, source),
          AmcatMetadataMapping(article, url),
          AmcatMetadataMapping(batch, project),
          AmcatMetadataMapping(article, headline),
          AmcatMetadataMapping(article, quote),
          AmcatMetadataMapping(source, sourcetype),
          ]
    def __str__(self):
        return "Amcat"

class AmcatMetadataField(Field):
    def __init__(self, datasource, concept, tables, column):
        Field.__init__(self, datasource, concept)
        self.tables = tables
        self.column = column

class AmcatMetadataMapping(Mapping):
    def __init__(self, a, b, cost=1.0):
        Mapping.__init__(self, a, b, cost, cost)
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
        #print sql_query[:200], len(values)
        result_dict = collections.defaultdict(list)
        for k, v in self.a.datasource.db.doQuery(sql_query):
            result_dict[k].append(v)
        #print "OK"

        return result_dict
    
    def mapmultiple(self, values, reverse):
        tables = set(self.a.tables) & set(self.b.tables)
        if len(tables) <> 1: raise Exception("Intersection not one!")
        table = tables.pop()

        result_dict = dict()
        selectcol = self.a.column if reverse else self.b.column
        filtercol = self.b.column if reverse else self.a.column

        #sql_query = "select %s, %s  from %s where %s in (%s)" % (filtercol,selectcol, table, filtercol, toolkit.quotesql(values))
        print sql_query
        result_dict = dict(self.a.datasource.db.doQuery(sql_query))
        #print "done!"
        
        for k, v in result_dict.iteritems():
            self.map(v, reverse)
        return 
        
if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB()
    
    from mst import getSolution
    from datasource import FunctionalDataModel
    import tabulator
    
    dm = FunctionalDataModel(getSolution)
    ads = AmcatMetadataSource(db, dm)
    dm.register(ads)
    
    print dm.getConcepts()
    
    project = dm.getConcept("project")
    art = dm.getConcept("article")
    medium = dm.getConcept("source")
    mediumtype = dm.getConcept("sourcetype")
    filters = {project : [368], art : [44134082,44135035, 44126401]  }
    select = [art, project, mediumtype]

    data = tabulator.tabulate(dm, select, filters)

    print " | ".join(map(lambda x: "%-15s" % x, select))
    print "-+-".join(["-"*15 for x in select])
    for row in data:
        print " | ".join(map(lambda x: "%-15s" % x, row))
