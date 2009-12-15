import xapian, dbtoolkit, toolkit
import collections, sources, project

from datasource import DataSource, Mapping, Field, FieldConceptMapping
from itertools import imap, izip

WEEKSQL = "cast(datepart(year, date) as varchar) + '/' + REPLICATE(0,2-LEN(cast(datepart(week, date) as varchar)))+ CONVERT(VARCHAR,cast(datepart(week, date) as varchar))"
DATESQL = "convert(varchar(10), date, 102)"
DATESQL = "convert(int, convert(varchar(10), date, 112)) "
WEEKSQL = "datepart(year,date) * 100 + datepart(week, date)"
YEARSQL = "datepart(year, date)"


def sourceFactory(db, id):
    return db.sources.lookupID(id)

class ConceptMapper(object):
    def __init__(self, db, targetclass):
        self.db = db
        self.targetclass = targetclass
    def map(self, value, reverse):
        if not reverse: return value.id
        return self.targetclass(self.db, value)    
	
class AmcatMetadataSource(DataSource):
    def __init__(self, db, datamodel): 
        self.db = db
	DataSource.__init__(self, self.createMappings(datamodel))
    def createMappings(self, datamodel):
        article = AmcatMetadataField(self, datamodel.getConcept("article"), ["articles"], "articleid")#, ConceptMapper(self.db, article.fromDB))
        batch = AmcatMetadataField(self, datamodel.getConcept("batch"), ["articles", "batches"], "batchid", ConceptMapper(self.db, project.Batch))
        headline = AmcatMetadataField(self, datamodel.getConcept("headline"), ["articles"], "headline")
        date = AmcatMetadataField(self, datamodel.getConcept("date"), ["articles"], DATESQL)
        week = AmcatMetadataField(self, datamodel.getConcept("week"), ["articles"], WEEKSQL)
        year = AmcatMetadataField(self, datamodel.getConcept("year"), ["articles"], YEARSQL)
        source = AmcatMetadataField(self, datamodel.getConcept("source"), ["articles","media"], "mediumid", ConceptMapper(self.db, sourceFactory))
        url = AmcatMetadataField(self, datamodel.getConcept("url"), ["articles"], "url")
        projectfield = AmcatMetadataField(self, datamodel.getConcept("project"),["batches"], "projectid", ConceptMapper(self.db, project.Project))
        sourcetype = AmcatMetadataField(self, datamodel.getConcept("sourcetype"),["media"], "type")
        return [
          AmcatMetadataMapping(article, batch),
          AmcatMetadataMapping(article, date),
          AmcatMetadataMapping(article, week),
          AmcatMetadataMapping(article, year, 1000),
          AmcatMetadataMapping(article, source),
          AmcatMetadataMapping(article, url),
          AmcatMetadataMapping(batch, projectfield),
          AmcatMetadataMapping(article, headline),
          AmcatMetadataMapping(source, sourcetype),
          ]
    def __str__(self):
        return "Amcat"

class AmcatMetadataField(Field):
    def __init__(self, datasource, concept, tables, column, conceptmapper=None):
        Field.__init__(self, datasource, concept)
        self.tables = tables
        self.column = column
        self.conceptmapper = conceptmapper
    def getConceptMapping(self):
        return FieldConceptMapping(self.concept, self, self.mapConcept)
    def mapConcept(self, value, reverse):
        if self.conceptmapper:
            return self.conceptmapper.map(value, reverse)
        return value

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
        
        result_dict = collections.defaultdict(list)
        for values in toolkit.splitlist(values, 1000):
            valuestr = ",".join(map(str, values))
            sql_query = "select %s, %s  from %s where %s in (%s)" % (filtercol,selectcol, table, filtercol, valuestr)
            for k, v in self.a.datasource.db.doQuery(sql_query):
                result_dict[k].append(v)

        return result_dict
        
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
