import collections
import logging; log = logging.getLogger(__name__)

from amcat.scripts.export_codingjobresults import ExportScript, FieldColumn, Row
from amcat.tools import toolkit
from amcat.model.coding import codingjob, annotationschema
from amcat.tools.table import table3, tableoutput
from amcat.model.ontology.object import Object
from amcat.model.ontology.tree import Tree


#from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()

def getTable(jobs, *args, **kargs):
    return DNNExportScript(*args, **kargs).getTable(jobs)

CATEGORIES = {"cat":2,"root":1,"class":0}


CODEBOOK_CACHE = {}
def getCodebook(codebook):
    if codebook.id not in CODEBOOK_CACHE:
        CODEBOOK_CACHE[codebook.id] = codebook
    return CODEBOOK_CACHE[codebook.id]

DIM_TREE = None
def getDimTree(db):
    global DIM_TREE
    if DIM_TREE is None:
        DIM_TREE = Tree(db, 5001)
    return DIM_TREE

class DNNFieldColumn(FieldColumn):
    def __init__(self, field, ontoption=None):
        log.debug("Created DNNFIeldColumn for %s / %s" % (field, ontoption))
                
        FieldColumn.__init__(self, field)
        self.ontoption = ontoption
        self.label = field.fieldname
        if self.ontoption:
            self.label += self.ontoption
            self.fieldname += ontoption
        self.codebook = getCodebook(self.field.serializer.codebook)
    def getCell(self, row):
        val = super(DNNFieldColumn, self).getCell(row)
        if val is None: return ""
        if not issubclass(self.field.getTargetType(), Object):
            return val
        val = self.codebook.getObject(val)
        if self.ontoption in CATEGORIES:
            val = self.codebook.categorise(val, date=row.art.date, depth=CATEGORIES[self.ontoption])[-1]
        elif self.ontoption == "dim":
            val = self.codebook.categorise(val, date=row.art.date, depth=2)[-1]
            if val:
                val = getDimTree(val.objekt.db).getParent(val)
                if val is None: return ""
        return val.objekt

class AggrQualColumn(FieldColumn):
    def __init__(self, field, ontoption='cat'):
        self.label = "aggrqual"
        self.ontoption = ontoption
        if ontoption != 'cat': self.label += ontoption
        FieldColumn.__init__(self, field, fieldname=self.label, label=self.label)

    def getCell(self, row):
        val = super(self.__class__, self).getCell(row)
        if val is None: return
        for fieldname in ("subject", "object"):
            field = self.field.schema.getField(fieldname)
            codebook = getCodebook(field.serializer.codebook)
            obj = annotationschema.getValue(self.getUnit(row), field)
            if not obj: continue
            omklap = codebook.categorise(obj, date=row.art.date, depth=CATEGORIES[self.ontoption],
                                         returnReverse=True, returnObject=False)[-1]
            log.debug("omklap for %s %s %s = %s" % (self.ontoption, fieldname, obj, omklap))
            
            if omklap: val *= -1
        return val
        
CODER_HIERARCHY = {206:280}
class DNNExportScript(ExportScript):
    def getColumnsForField(self, field):
        if issubclass(field.getTargetType(), Object):
            #for option in [None, "cat", "root", "class", "dim"]:
            for option in [None, "cat", "root", "dim"]:
                yield DNNFieldColumn(field, option)
        else:
            for col in super(DNNExportScript, self).getColumnsForField(field):
                yield col
        if field.fieldname == 'quality':
            #yield AggrQualColumn(field, article)#, ontoption=option)
            for option in ["cat"]:
                yield AggrQualColumn(field, ontoption=option)

    def getMetaColumns(self):
        return super(DNNExportScript, self).getMetaColumns() + [
            #table3.ObjectColumn("parnr", lambda row: row.cs and row.cs.sentence.parnr, fieldtype=int),
            #table3.ObjectColumn("sentnr", lambda row: row.cs and row.cs.sentence.sentnr, fieldtype=int),
            table3.ObjectColumn("Mediumid", lambda row: row.art.source.id, fieldtype=int),
            ]

    def getCodedArticles(self, jobs):
        casPerArt = collections.defaultdict(set)
        for ca in codingjob.getCodedArticlesFromCodingjobs(jobs):
            casPerArt[ca.article].add(ca)
        for cas in casPerArt.values():
            yield sorted(cas, key=lambda ca:CODER_HIERARCHY.get(ca.set.coder.id, ca.set.coder.id))[0]
            

def test():
    from amcat.db import dbtoolkit
    from amcat.model.coding import codedsentence

    from amcat.tools.logging import amcatlogging
    amcatlogging.setup()
    
    db = dbtoolkit.amcatDB(profile=True)
    arrowid = 686970
    cs = codedsentence.CodedSentence(db, arrowid)
    ca = cs.codedarticle
    job = ca.codingjobset.job
    row = Row(ca, cs)
    print row
    print row.cs
    print row.cs.values
    
    s = DNNExportScript()
    cols = s.getColumns([job])
    for col in cols:
        print col, col.getCell(row)

    
if __name__ == '__main__':
    test()
    #DNNExportScript().runFromCommand()
    
