import collections
import datetime
import logging; log = logging.getLogger(__name__)

from amcat.tools.table import table3, tableoutput, table2spss
from amcat.tools import toolkit, idlabel
from amcat.tools.cachable import cacher
from amcat.tools.logging import amcatlogging, ticker
from amcat.model.coding.annotationschema import FieldColumn
from amcat.model.coding import codingjob

from amcat.scripts import externalscripts
from amcat.db import dbtoolkit

BUFFERSIZE = 500

amcatlogging.infoModule()
amcatlogging.infoModule('progress')

class Row(object):
    def __init__(self, ca, cs):
        self.ca = ca
        self.cs = cs
        self.art = ca.article
        
class ExportScript(externalscripts.ExternalScriptBase):

    def _run(self, jobidlist, out, err, exportformat='csv', requireSentence=False, rowlimit=None):
        super(ExportScript, self)._run(jobidlist, out, err)
        self.rowlimit = rowlimit
        #self.rowlimit = 100
        
        with self.pm.monitored("Extracting data", 100):
            log.info("Starting export of data %r to format %s" % (jobidlist, exportformat))
            db = dbtoolkit.amcatDB(username='app', password='eno=hoty', profile=True)
            jobs = [codingjob.Codingjob(db, cjid) for cjid in toolkit.intlist(jobidlist)]
            self.requireSentence = requireSentence
            self.allowidlabel = False
            self.pm.worked(5)
            t = self.getTable(jobs, self.pm.submonitor(10))
            log.info("Table created, starting export")
            self.exportTable(t, exportformat, self.pm.submonitor(80, name="export"))
            self.pm.worked(5)
        db.printProfile()

    def exportTable(self, table, format, monitor):
        if format == 'spss':
            #w = open('/tmp/log.spss', 'w')
            #table2spss.table2spss(table, w)
            fn = table2spss.table2sav(table, monitor=monitor)
            
            log.info("Saved as %s" % fn)
            self.out.write(open(fn).read())
        else:
            tableoutput.table2csv(table, outfile=self.out, monitor=monitor)
        log.info("Done!")
        
    
    def getTable(self, jobs, monitor):
        with monitor.monitored("Setting up table", 100) as pm:
            self.cacheJobs(jobs)
            pm.worked(20)
            self.cacheSchemas(jobs)
            pm.worked(20)
        #log.debug(jobs[0].db.printProfileHTML())
            log.debug("Setting up table - Creating row generator")
            rows = toolkit.splitlist(self.getRows(jobs), buffercall=self.cacheRows, itemsperbatch=BUFFERSIZE, yieldelements=True)
            pm.worked(20)
            log.debug("Setting up table - Creating columns")
            cols = self.getColumns(jobs)
            pm.worked(20)
            t = table3.ObjectTable(rows, cols)
            pm.worked(20)
            log.debug("Setting up table - Done")
            return t

    def cacheJobs(self, jobs):
        cacher.cache(jobs, "unitSchema", "articleSchema", "name", sets=dict(coder=["username"]))

    def cacheSchemas(self, jobs):
        schemas = set()
        for j in jobs:
            schemas |= set((j.unitSchema, j.articleSchema))
        cacher.cache(schemas, "fields","location")

        
    def cacheMeta(self, rows):
        return
        cas = set(row.ca for row in rows)
        cacher.cacheMultiple(cas, "article")
        cacher.cacheMultiple(set(ca.article for ca in cas),
                               "encoding", "headline", "date", "length", "pagenr", "source")
        cacher.cacheMultiple(set(ca.article.source for ca in cas), "name")
        css = set(row.cs for row in rows if row.cs)
        #cacher.cache(css, sentence=["parnr","sentnr"])
        
        
    def getCodedArticles(self, jobs):
        cacher.cache(jobs, sets=["articles"])
        return codingjob.getCodedArticlesFromCodingjobs(jobs)
        
    def getRows(self, jobs):
        i = [0]
        log.debug("Getting coded articles")
        cas = list(self.getCodedArticles(jobs))
        log.debug("Got coded articles")
        n = len(cas)
        ndone = 0
        def dobuffer(arts):
            j =  i[0] +len(arts)
            pct = int(float(i[0] * 100) / n)
            log.debug("Getting articles %i - %i / %i (%i%%)" % (i[0], j, n, pct))
            i[0] = j
            cacher.cache(arts, "sentences", "article")
            #log.debug(jobs[0].db.printProfileHTML())
        for ca in toolkit.splitlist(cas, BUFFERSIZE, dobuffer, yieldelements=True):
            sents = False
            for cs in ca.sentences:
                sents = True
                yield Row(ca,cs)
                ndone += 1
                if self.rowlimit and ndone >= self.rowlimit: return
                                
            if (not sents) and (not self.requireSentence):
                yield Row(ca, None)
                ndone += 1
                if self.rowlimit and ndone >= self.rowlimit: return


    def cacheRows(self, rows):
        self.cacheMeta(rows)
        self.cacheFields(rows)

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
                table3.ObjectColumn("CodingJob", lambda row: row.ca.set.job, fieldtype=idlabel.IDLabel),
                table3.ObjectColumn("Set", lambda row: row.ca.set.setnr, fieldtype=int),
                table3.ObjectColumn("Coder", lambda row: row.ca.set.coder, fieldtype=idlabel.IDLabel),
                table3.ObjectColumn("ArticleId", lambda row: row.art.id, fieldtype=int),
                table3.ObjectColumn("Medium", lambda row: row.art.source, fieldtype=idlabel.IDLabel),
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
    
    def _getOutputType(self, exportformat='csv', *args):
        """How to interpret the output file, i.e. return its (mime) type"""
        if exportformat == 'spss':
            return "application/spss"
        elif exportformat == "csv":
            return "text/csv"
        else:
            return super(ExportScript, self)._getOutputType(*args)
    def _getOutputExtension(self, exportformat='csv', *args):
        """Suggest an extension for the output file"""
        if exportformat == 'spss':
            return ".sav"
        elif exportformat == "csv":
            return ".csv"
        else:
            return super(ExportScript, self)._getOutputExtension(*args)
    
if __name__ == '__main__':
    ExportScript().runFromCommand()
