try:
    from export_codingjobresults import ExportScript, FieldColumn, Row
except ImportError, e:
    try:
        from mod_python import apache
        mod = apache.import_module("scripts/export_codingjobresults")
        ExportScript = mod.ExportScript
        FieldColumn = mod.FieldColumn
        Row = mod.Row
    except ImportError, e2:
        import sys
        raise ImportError("Could not import from base class, tried simple import using path\n\n%s\n\n, then tried via apache, but nothing helped\n\n%s\n%s"% (sys.path, e, e2))


import toolkit
import codingjob
import table3, tableoutput
import categorise
import collections
import ont
import cachable
from codingjob import getValue

import logging; log = logging.getLogger(__name__)
import amcatlogging; amcatlogging.debugModule()

def getTable(jobs, *args, **kargs):
    return DNNExportScript(*args, **kargs).getTable(jobs)

CATEGORIES = {"cat":2,"root":1,"class":0}

class DNNFieldColumn(FieldColumn):
    def __init__(self, field, article, ontoption=None):
        FieldColumn.__init__(self, field, article)
        self.ontoption = ontoption
        self.label = field.fieldname
        if self.ontoption:
            self.label += self.ontoption
            self.fieldname += ontoption
        #log.debug("Created DNNFIeldColumn for %s / %s" % (field, ontoption))
    def getCell(self, row):
        val = super(DNNFieldColumn, self).getCell(row)
        if val is None: return ""
        if not issubclass(self.field.getTargetType(), ont.Object):
            return val
        val = self.field.serializer.set.getBoundObject(val)
        if self.ontoption in CATEGORIES:
            val = self.field.serializer.set.categorise(val, date=row.art.date, depth=[CATEGORIES[self.ontoption]])[0]
        elif self.ontoption == "dim":
            val = self.field.serializer.set.categorise(val, date=row.art.date, depth=[1])[0]
            if val:
                val = val.objekt.parents.get(ont.Class(val.objekt.db, 5001))
        return val

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
            obj = getValue(self.getUnit(row), field)
            if self.ontoption in CATEGORIES:
                omklap = field.serializer.set.categorise(obj, date=row.art.date, depth=[CATEGORIES[self.ontoption]], returnOmklap=True, returnObjects=False)
                #log.debug("omklap for %s %s %s = %s" % (self.ontoption, fieldname, obj, omklap))
                                
            elif self.ontoption == "dim":
                cat, omklap = field.serializer.set.categorise(obj, date=row.art.date, depth=[2], returnOmklap=True)
                cat = cat[0]
                if val:
                    dim = cat.objekt.parents.get(ont.Class(cat.objekt.db, 5001))
                    if dim:
                        omklap2 = ont.getOmklap(cat.objekt.db, dim, cat)
                        omklap *= omklap2
                    else:
                        omklap = 0
                else:
                    omklap = 0
            val *= omklap
        return val
        
CODER_HIERARCHY = {206:280}
class DNNExportScript(ExportScript):
    def getColumn(self, field, article):
        if issubclass(field.getTargetType(), ont.Object):
            for option in [None, "cat", "root", "class", "dim"]:
                yield DNNFieldColumn(field, article, option)
        else:
            yield DNNFieldColumn(field, article)
        if field.fieldname == 'quality':
            #yield AggrQualColumn(field, article)#, ontoption=option)
            for option in ["cat", "root"]:
                yield AggrQualColumn(field, article, ontoption=option)

    def getMetaColumns(self):
        return super(DNNExportScript, self).getMetaColumns() + [
            table3.ObjectColumn("parnr", lambda row: row.cs and row.cs.sentence.parnr, fieldtype=int),
            table3.ObjectColumn("sentnr", lambda row: row.cs and row.cs.sentence.sentnr, fieldtype=int),
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
        cachable.cache(jobs, sets=dict(articles=["article"], coder=[]))
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

    db.printProfile() 

    
if __name__ == '__main__':
    DNNExportScript().runFromCommand()
    
