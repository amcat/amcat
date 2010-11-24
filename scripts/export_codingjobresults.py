import table3
import codingjob
import toolkit
import collections
import cachable
import ont
from idlabel import IDLabel
from annotationschema import FieldColumn
import datetime

import logging; log = logging.getLogger(__name__)
import ticker

import tableoutput
import table2spss

import externalscripts

import dbtoolkit

BUFFERSIZE = 500



class Row(object):
    def __init__(self, ca, cs):
        self.ca = ca
        self.cs = cs
        self.art = ca.article
        
class ExportScript(externalscripts.ExternalScript):
    def call(self, jobs, exportformat='csv'):
        return super(ExportScript, self).call(jobs, exportformat)
    
    def run(self, data, exportformat='csv', requireSentence=False):
        import amcatlogging
        amcatlogging.debugModule("tableoutput", "table2spss")
        amcatlogging.infoModule()
        log.info("Starting export of data %s to format %s" % (data, exportformat))
        db = dbtoolkit.amcatDB(username='app', password='eno=hoty')
        jobs = [codingjob.Codingjob(db, cjid) for cjid in toolkit.intlist(data)]
        self.requireSentence = requireSentence
        self.allowidlabel = False
        t = self.getTable(jobs)
        self.exportTable(t, exportformat)

    def exportTable(self, table, format):
        if format == 'spss':
            fn = toolkit.tempfilename(suffix=".sav")
            table2spss.table2spss(table, saveas=fn)
            log.info("Saved as %s" % fn)
        else:
            tableoutput.table2csv(table)
        log.info("Done!")
        
    
    def getTable(self, jobs):
        log.debug("Setting up table - caching jobs/schemas")
        self.cacheJobs(jobs)
        self.cacheSchemas(jobs)
        #log.debug(jobs[0].db.printProfileHTML())
        log.debug("Setting up table - Creating row generator")
        rows = toolkit.splitlist(self.getRows(jobs), buffercall=self.cacheRows, itemsperbatch=BUFFERSIZE, yieldelements=True)
        log.debug("Setting up table - Creating columns")
        cols = self.getColumns(jobs)
        t = table3.ObjectTable(rows, cols)
        log.debug("Setting up table - Done")
        return t

    def cacheJobs(self, jobs):
        cachable.cache(jobs, "unitSchema", "articleSchema", "name", sets=dict(coder=["username"]))

    def cacheSchemas(self, jobs):
        schemas = set()
        for j in jobs:
            schemas |= set((j.unitSchema, j.articleSchema))
        cachable.cache(schemas, "fields","location","params")

        
    def cacheMeta(self, rows):
        cas = set(row.ca for row in rows)
        cachable.cacheMultiple(cas, "article")
        cachable.cacheMultiple(set(ca.article for ca in cas),
                               "encoding", "headline", "date", "length", "pagenr", "source")
        cachable.cacheMultiple(set(ca.article.source for ca in cas), "name")
        css = set(row.cs for row in rows if row.cs)
        #cachable.cache(css, sentence=["parnr","sentnr"])
        
        
    def getCodedArticles(self, jobs):
        cachable.cache(jobs, sets=["articles"])
        return codingjob.getCodedArticlesFromCodingjobs(jobs)
        
    def getRows(self, jobs):
        i = [0]
        log.debug("Getting coded articles")
        cas = list(self.getCodedArticles(jobs))
        log.debug("Got coded articles")
        n = len(cas)
        def dobuffer(arts):
            j =  i[0] +len(arts)
            pct = int(float(i[0] * 100) / n)
            log.debug("Getting articles %i - %i / %i (%i%%)" % (i[0], j, n, pct))
            i[0] = j
            cachable.cache(arts, "sentences", "article")
            #log.debug(jobs[0].db.printProfileHTML())
        for ca in toolkit.splitlist(cas, BUFFERSIZE, dobuffer, yieldelements=True):
            sents = False
            for cs in ca.sentences:
                sents = True
                yield Row(ca,cs)
            if (not sents) and (not self.requireSentence):
                yield Row(ca, None)


    def cacheRows(self, rows):
        tick = ticker.Ticker(log=log)
        tick.warn(">>>>>>>>")
        self.cacheMeta(rows)
        tick.warn("--------")
        self.cacheFields(rows)
        tick.warn("<<<<<<<<")

    def cacheFields(self, rows):
        units = collections.defaultdict(set) # schema : units
        for row in rows:
            ca = row.ca
            job = ca.set.job
            units[job.articleSchema].add(ca)
            cs = row.cs
            if cs: units[job.unitSchema].add(cs)
       # for schema, units in units.iteritems():
            #schema.cacheMany(units)
        

        
        
    def getMetaColumns(self):
            return [
                table3.ObjectColumn("CodingJob", lambda row: row.ca.set.job, fieldtype=IDLabel),
                table3.ObjectColumn("Set", lambda row: row.ca.set.setnr, fieldtype=int),
                table3.ObjectColumn("Coder", lambda row: row.ca.set.coder, fieldtype=IDLabel),
                table3.ObjectColumn("ArticleId", lambda row: row.art.id, fieldtype=int),
                table3.ObjectColumn("Medium", lambda row: row.art.source, fieldtype=IDLabel),
                table3.ObjectColumn("Pagenr", lambda row: row.art.pagenr, fieldtype=int),
                table3.ObjectColumn("Length", lambda row: row.art.length, fieldtype=int),
                table3.ObjectColumn("Date", lambda row: row.art.date, fieldtype=datetime.datetime),
                table3.ObjectColumn("Headline", lambda row: row.art.headline, fieldtype=str),
                table3.ObjectColumn("CodingjobArticleid", lambda row: row.ca.id, fieldtype=int),
                table3.ObjectColumn("Arrowid", lambda row: row.cs and row.cs.id, fieldtype=int),
                ]
    
    def getSchemaFields(self, jobs, article):
        fields = []
        for job in jobs:
            schema = job.articleSchema if article else job.unitSchema
            sfields = schema.fields
            for field in sfields:
                if field not in fields: fields.append(field)
        return fields

    def getColumn(self, field, article):
        return [FieldColumn(field, article)]
    
    def getAnnotationColumns(self, jobs, article):
        for field in self.getSchemaFields(jobs, article):
            for column in self.getColumn(field, article):
                yield column
            

    def getArticleAnnotationColumns(self, jobs):
        return self.getAnnotationColumns(jobs, True)
    def getUnitAnnotationColumns(self, jobs):
        return self.getAnnotationColumns(jobs, False)
            
    def getColumns(self, jobs):
        return (self.getMetaColumns()
                + list(self.getArticleAnnotationColumns(jobs))
                + list(self.getUnitAnnotationColumns(jobs)))

if __name__ == '__main__':
    ExportScript().runFromCommand()
