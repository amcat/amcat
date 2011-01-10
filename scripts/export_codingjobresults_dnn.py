import collections
import logging; log = logging.getLogger(__name__)

from amcat.scripts.export_codingjobresults import ExportScript, FieldColumn, Row
from amcat.tools import toolkit
from amcat.model.coding import codingjob
from amcat.tools.table import table3, tableoutput
from amcat.model.ontology.object import Object
from amcat.model.ontology.tree import Tree
from amcat.model.coding.codingjob import getValue

from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()

def getTable(jobs, *args, **kargs):
    return DNNExportScript(*args, **kargs).getTable(jobs)

CATEGORIES = {"cat":2,"root":1,"class":0}

CODEBOOK_CACHE = {}

def getCodebook(codebook):
    if codebook.id not in CODEBOOK_CACHE:
	CODEBOOK_CACHE[codebook.id] = codebook
    return CODEBOOK_CACHE[codebook.id]

class DNNFieldColumn(FieldColumn):
    def __init__(self, field, article, ontoption=None):
	log.debug("Created DNNFIeldColumn for %s / %s" % (field, ontoption))
		
        FieldColumn.__init__(self, field, article)
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
            val = self.codebook.categorise(val, date=row.art.date, depth=[1])[0]
            if val:
                val = val.objekt.parents.get(Tree(val.objekt.db, 5001))
        return val.objekt

class AggrQualColumn(FieldColumn):
    def __init__(self, field, article, ontoption='cat'):
        self.label = "aggrqual"
        self.ontoption = ontoption
        if ontoption != 'cat': self.label += ontoption
        FieldColumn.__init__(self, field, article, fieldname=self.label, label=self.label)

    def getCell(self, row):
        val = super(self.__class__, self).getCell(row)
        if val is None: return
        for fieldname in ("subject", "object"):
            field = self.field.schema.getField(fieldname)
	    codebook = getCodebook(field.serializer.codebook)
            obj = getValue(self.getUnit(row), field)
            omklap = codebook.categorise(obj, date=row.art.date, depth=CATEGORIES[self.ontoption],
					 returnReverse=True, returnObject=False)[-1]
            log.debug("omklap for %s %s %s = %s" % (self.ontoption, fieldname, obj, omklap))
            
	    if omklap: val *= -1
        return val
        
CODER_HIERARCHY = {206:280}
class DNNExportScript(ExportScript):
    def getColumn(self, field, article):
        if issubclass(field.getTargetType(), Object):
            #for option in [None, "cat", "root", "class", "dim"]:
	    for option in [None, "cat", "root"]:
                yield DNNFieldColumn(field, article, option)
        else:
            yield FieldColumn(field, article)
        if field.fieldname == 'quality':
            #yield AggrQualColumn(field, article)#, ontoption=option)
            for option in ["cat"]:
                yield AggrQualColumn(field, article, ontoption=option)

    def getMetaColumns(self):
        return super(DNNExportScript, self).getMetaColumns() + [
            #table3.ObjectColumn("parnr", lambda row: row.cs and row.cs.sentence.parnr, fieldtype=int),
            #table3.ObjectColumn("sentnr", lambda row: row.cs and row.cs.sentence.sentnr, fieldtype=int),
            table3.ObjectColumn("Mediumid", lambda row: row.art.source.id, fieldtype=int),
            ]

    def getCodedArticles(self, jobs):
        # Need to fix caching FK relations with composite keys !
        #cachable.cacheMultiple(jobs, "sets")
        #toolkit.ticker.warn("--- !b")
        #sets = []
        #for j in jobs: sets += j.sets
        #cachable.cacheMultiple(sets, "articles", "coder")
        #toolkit.ticker.warn("--- !c")
        #cas = []
        #for set in sets: cas += set.articles
        #cachable.cacheMultiple(cas, "article")
        #cachable.cache(jobs, sets=dict(articles=["article"], coder=[]))
        casPerArt = collections.defaultdict(set)
        for ca in codingjob.getCodedArticlesFromCodingjobs(jobs):
            casPerArt[ca.article].add(ca)
        for cas in casPerArt.values():
            yield sorted(cas, key=lambda ca:CODER_HIERARCHY.get(ca.set.coder.id, ca.set.coder.id))[0]
            
        
    def cacheField(self, field):
        if isinstance(field, codingjob.OntologyAnnotationSchemaField):
            toolkit.ticker.warn(">>>>>>>>>>> %s" % field.fieldname)
            field.set.cacheHierarchy()
            toolkit.ticker.warn("<<<<<<<<<< %s" % field.fieldname)
        else:
            super(DNNExportScript, self).cacheField(field)

def test():
    import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True)
    db.beforeQueryListeners.add(lambda a: toolkit.ticker.warn(a[:250]))
    #ids = db.doQuery("select codingjobid from codingjobs where projectid=388")
    #ids = [id for (id,) in ids]
    ids = [3789]
    #ids = [4240]
    toolkit.ticker.warn(ids)
    jobs = [codingjob.Codingjob(db, id) for id in ids]
    t = DNNExportScript().getTable(jobs)
    import table2spss
    table2spss.table2sav(t, "/tmp/test.sav")


    
if __name__ == '__main__':
    DNNExportScript().runFromCommand()
    
