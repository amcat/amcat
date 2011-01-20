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

"""
Default export script and base class for custom exporters.

Main class is the ExportScript, which derives from ExternalScriptBase. This
class can be used to export a selection of codingjobs to different formats
through a Table object. Steps:

    1. Create the right columns based on the coding schema(s)
    2. Create a row generator that yields all coded units
    3. Export the resulting table to the chosen format
"""

from __future__ import print_function, absolute_import

import collections
import datetime
import itertools
import logging; log = logging.getLogger(__name__)

from amcat.tools.table import table3, tableoutput, table2spss
from amcat.tools import toolkit, idlabel
from amcat.tools.cachable import cacher
from amcat.tools.logging import amcatlogging, ticker, progress
from amcat.model.coding.annotationschema import FieldColumn
from amcat.model.coding import codingjob

from amcat.scripts import externalscripts
from amcat.db import dbtoolkit

BUFFERSIZE = 500

amcatlogging.debugModule()
amcatlogging.infoModule('progress')

class Row(object):
    "Class representing a row in a coding job export, with a coded article and possibly coded sentence"
    def __init__(self, ca, cs):
        self.ca = ca
        self.cs = cs
        self.art = ca.article
        
class ExportScript(externalscripts.ExternalScriptBase):
    """
    Default CodingJob Export Script and base class for custom scripts.

    Data argument for this script is a list of codingjobids.
    Optional 'exportformat' argument is a string describing an export format (eg csv/spss)

    ._run first class .getTable to create a table, which calls .getRows and .getcolumns.
    .exportTable is then called to export the table in the requested format.

    Most functions are called with a progress monitor argument to supply feedback to the end user.

    A number of .cacheX functions exist to facilitate efficient database access.
    """

    def __init__(self):
        super(ExportScript, self).__init__()
        self.rowlimit = None
        self.requireSentence=False
    
    def _run(self, jobidlist, out, err, exportformat='csv', requireSentence=False, rowlimit=None):
        "Entry point for exporting, sets up db and monitoring and calls getTable and exportTable"
        super(ExportScript, self)._run(jobidlist, out, err)
        self.rowlimit = rowlimit
        #self.rowlimit = 100
        
        with self.pm.monitored("Extracting data", 100):
            log.info("Starting export of data %r to format %s" % (jobidlist, exportformat))
            db = dbtoolkit.amcatDB(username='app', password='eno=hoty', driver="SQLServer")
            jobs = [codingjob.Codingjob(db, cjid) for cjid in toolkit.intlist(jobidlist)]
            self.requireSentence = requireSentence
            self.allowidlabel = False
            self.pm.worked(5)
            t = self.getTable(jobs, self.pm.submonitor(10), self.pm.submonitor(80, name="export"))
            log.info("Table created, starting export")
            self.exportTable(t, exportformat)
            self.pm.worked(5)
        #db.printProfile()

    def exportTable(self, table, format):
        """Export the table to self.out in the requested format
        @type table: L{Table<amcat.tools.table.table3.Table>}
        @param table: the table to export
        @type format: string
        @param format: the export format to use
        @param monitor: a progress monitor to report feedback to
        """
        if format == 'spss':
            #w = open('/tmp/log.spss', 'w')
            #table2spss.table2spss(table, w)
            fn = table2spss.table2sav(table)
            log.info("Saved as %s" % fn)
            self.out.write(open(fn).read())
        else:
            tableoutput.table2csv(table, outfile=self.out)
        log.info("Done!")
        
    
    def getTable(self, jobs, monitor=progress.NullMonitor(), exportmonitor=progress.NullMonitor()):
        """Create a L{Table<amcat.tools.table.table3.Table>} object from the given jobs

        The resulting Table object uses a row generator and column functions to create the
        data as needed, so the 'hard work' is only done when actually using the table.

        @param jobs: a sequence of CodingJob objects
        @param monitor: a progress monitor to report setup feedback to
        @param exportmonitor: a progress monitor to report iteration feedback to
        @return: a Table object
        """
        with monitor.monitored("Setting up table", 100) as pm:
            self.cacheInitial(jobs)
            pm.worked(40)
            log.debug("Setting up table - Creating row generator")
            rows = toolkit.splitlist(self.getRows(jobs, exportmonitor), buffercall=self.cacheRows, itemsperbatch=BUFFERSIZE, yieldelements=True)
            if self.rowlimit:
                rows = itertools.islice(rows, stop=self.rowlimit)
            pm.worked(20)
            log.debug("Setting up table - Creating columns")
            cols = self.getColumns(jobs)
            pm.worked(20)
            t = table3.ObjectTable(rows, cols)
            pm.worked(20)
            log.debug("Setting up table - Done")
            return t

    def cacheInitial(self, jobs):
        """Cache initial values, i.e. codingjob schema"""
        codingjob.cacheCodingJobs(jobs, articles=False)
        codebooks = set()
        for job in jobs:
            for schema in (job.unitSchema, job.articleSchema):
                for field in schema.fields:
                    if field.codebook: codebooks.add(field.codebook)
        for c in codebooks:
            c.cacheHierarchy()
            c.cacheLabels()

    def cacheSentences(self, codedarticles):
        """Cache the codedsentences for these codedarticles"""
        log.debug("Caching sentences for %i codedarticles" % len(codedarticles))
        cacher.cache(codedarticles, "sentences")
        
    def getCodedArticles(self, jobs):
        """Return the codedarticles objects in these jobs"""
        return codingjob.getCodedArticlesFromCodingjobs(jobs, cacheValues=False)
    
    def getRows(self, jobs, monitor):
        """Yield the Rows to be extracted from the jobs"""
        log.debug("Getting coded articles")
        cas = list(self.getCodedArticles(jobs))
        log.debug("Iterating over articles to return rows")
        with monitor.monitored("Exporting", units=len(cas)):
            for ca in toolkit.splitlist(cas, BUFFERSIZE, self.cacheSentences, yieldelements=True):
                monitor.worked()
                for row in self.getRowsFromCodedArticle(ca):
                    yield row

    def getRowsFromCodedArticle(self, codedarticle):
        """yield the rows to be extracted from this coded article
        Yields one Row for each codedsentence in each article, and
        (unless self.requireSentence) one row for each codedarticle
        with no codedsentences
        """
        sents = False
        for cs in codedarticle.sentences:
            sents = True
            yield Row(codedarticle,cs)
        if not sents and (not self.requireSentence):
            yield Row(codedarticle, None)
                
                
    def cacheRows(self, rows):
        """Cache the values for these row objects
        Calls cacheMeta and cacheFields with the codedarticles and codedsentences
        """
        log.debug("Caching values for %i rows" % len(rows))
        cas = set(row.ca for row in rows)
        css = set(row.cs for row in rows if row.cs)
        self.cacheMeta(cas, css)
        self.cacheFields(cas, css)

    def cacheMeta(self, codedarticles, codedsentences):
        """Cache meta fields (headline, parnr etc.) for these articles and sentences"""
        cacher.cache(codedarticles, article=dict(headline=[], date=[], length=[], pagenr=[], source=["name"]))
        cacher.cache(codedsentences, sentence=["parnr","sentnr"])
        sets = (ca.set for ca in codedarticles)
        cacher.cache(sets, coder="username")

    def cacheFields(self,  codedarticles, codedsentences):
        """Cache the coded values for these articles and sentences"""
        cacher.cache(codedarticles, "values")
        cacher.cache(codedsentences, "values")
        
    def getMetaColumns(self):
        """Get Columns reprsenting meta fields (articleid, headline etc)
        @returns: a sequence of L{Column<amcat.tools.table.table3.Column>} objects """
        def getDate(row):
            d = row.art.date
            d2 = toolkit.toDate(d)
            return d
        
        return [
            table3.ObjectColumn("CodingJob", lambda row: row.ca.set.job, fieldtype=idlabel.IDLabel),
            table3.ObjectColumn("Set", lambda row: row.ca.set.setnr, fieldtype=int),
            table3.ObjectColumn("Coder", lambda row: row.ca.set.coder, fieldtype=idlabel.IDLabel),
            table3.ObjectColumn("ArticleId", lambda row: row.art.id, fieldtype=int),
            table3.ObjectColumn("Medium", lambda row: row.art.source, fieldtype=idlabel.IDLabel),
            table3.ObjectColumn("Pagenr", lambda row: row.art.pagenr, fieldtype=int),
            table3.ObjectColumn("Length", lambda row: row.art.length, fieldtype=int),
            #table3.ObjectColumn("Date", lambda row: row.art.date, fieldtype=datetime.datetime),
            table3.ObjectColumn("Date", getDate, fieldtype=datetime.datetime),
            table3.ObjectColumn("Headline", lambda row: row.art.headline, fieldtype=str),
            table3.ObjectColumn("CodingjobArticleid", lambda row: row.ca.id, fieldtype=int),
            table3.ObjectColumn("Arrowid", lambda row: row.cs and row.cs.id, fieldtype=int),
            ]


    def getColumns(self, jobs):
        """Create the columns for the table to be exported
        Combines the results of getMetaCoilumns, getArticleAnnotationColumns, and getUnitAnnotationColumns
        @returns: a sequence of L{Column<amcat.tools.table.table3.Column>} objects """
        
        return (self.getMetaColumns()
                + list(self.getArticleAnnotationColumns(jobs))
                + list(self.getUnitAnnotationColumns(jobs)))
    
    def getSchemaFields(self, jobs, articlecodings):
        """get the annotationschemafields corresponding to these jobs
        @param jobs: a sequence of CodingJob objects
        @param isarticle: if True, return article annotation schema fields, otherwise unit fields
        @returns: a sequence of L{Column<amcat.tools.table.table3.Column>} objects """

        getfields = ((lambda job: job.articleSchema.fields) if articlecodings else
                     (lambda job: job.unitSchema.fields))
        return toolkit.unique(toolkit.flatten(itertools.imap(getfields, jobs)))

    def getColumnsForField(self, field):
        """get the column(s) representing this schemafield"""
        return [FieldColumn(field)]
    
    def getAnnotationColumns(self, jobs, articlecodings):
        """Create the annotationcolumns for these jobs"""
        for field in self.getSchemaFields(jobs, articlecodings):
            for column in self.getColumnsForField(field):
                yield column
            

    def getArticleAnnotationColumns(self, jobs):
        """Create the article annotation columns for these jobs
        returns getAnnotationColumns(jobs, True)"""
        return self.getAnnotationColumns(jobs, True)
    def getUnitAnnotationColumns(self, jobs):
        """Create the unit annotation columns for these jobs
        returns getAnnotationColumns(jobs, True)"""
        return self.getAnnotationColumns(jobs, False)
            
    
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
