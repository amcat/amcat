import collections
import logging; log = logging.getLogger(__name__)

from amcat.scripts.export_codingjobresults import ExportScript, FieldColumn, Row
from amcat.tools import toolkit
from amcat.model.coding import codingjob, annotationschema
from amcat.tools.table import table3, tableoutput
from amcat.model.ontology.object import Object
from amcat.model.ontology.tree import Tree

from amcat.scripts import netcolumn #TODO find a better home


#from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()

def getTable(jobs, *args, **kargs):
    return DNNExportScript(*args, **kargs).getTable(jobs)

        
CODER_HIERARCHY = {206:280}
class DNNExportScript(ExportScript):
    def getColumnsForField(self, field):
        # yield default columns
        for col in super(DNNExportScript, self).getColumnsForField(field):
            yield col
        # yield extra columns
        for col in netcolumn.getColumnsForField(field):
            yield col

    def getMetaColumns(self):
        return super(DNNExportScript, self).getMetaColumns() + [
            table3.ObjectColumn("parnr", lambda row: row.cs and row.cs.sentence.parnr, fieldtype=int),
            table3.ObjectColumn("sentnr", lambda row: row.cs and row.cs.sentence.sentnr, fieldtype=int),
            table3.ObjectColumn("Mediumid", lambda row: row.art.source.id, fieldtype=int),
            ]

    def getCodedArticles(self, jobs):
        casPerArt = collections.defaultdict(set)
        for ca in codingjob.getCodedArticlesFromCodingjobs(jobs):
            casPerArt[ca.article].add(ca)
        for cas in casPerArt.values():
            yield sorted(cas, key=lambda ca:CODER_HIERARCHY.get(ca.set.coder.id, ca.set.coder.id))[0]


    def getColumns(self, jobs):
        if list(jobs):
            return super(DNNExportScript, self).getColumns(jobs) + netcolumn.getArrowColumns(list(jobs)[0].unitSchema)
        else:
            return super(DNNExportScript, self).getColumns(jobs)

def lbl(x):
    from amcat.tools import idlabel
    if x is None: return "-"
    if isinstance(x, idlabel.IDLabel): return x.idlabel()
    return unicode(x)
            
def test():
    from amcat.db import dbtoolkit
    from amcat.model.coding import codedsentence

    from amcat.tools.logging import amcatlogging
    amcatlogging.setup()
    
    db = dbtoolkit.amcatDB(profile=True)
    arrowid = 686970
    arrowids = 586414, 586481, 585930, 585766, 585769, 585737, 585917
    #arrowids = [585737,585917,591758]
    arrowids = [586414, 586481, 585769]
    
    
    for arrowid in arrowids:
        cs = codedsentence.CodedSentence(db, arrowid)
        ca = cs.codedarticle
        job = ca.codingjobset.job
        
        s = DNNExportScript()
        rows = [s.createRow(ca, cs)]
        
        for row in rows:
            print "====== %s: %s ---%s(%+1.1f)--> %s =====" % (row.cs.id, row.cs.values.subject, row.cs.values.predicate, row.cs.values.quality, row.cs.values.object)
            print cs.sentence.article.date

            cols = netcolumn.getArrowColumns(job.unitSchema)
            for col in cols:
                c = col.getCell(row)
                print col, lbl(c)

            for field in "subject", "object", "quality":
                print "---- %s ----" % field
                cols = s.getColumnsForField(job.unitSchema.getField(field))
                for col in cols:
                    print col, lbl(col.getCell(row)).encode('utf-8')
            print

    
if __name__ == '__main__':
    test()
    #DNNExportScript().runFromCommand()
    
