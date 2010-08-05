import user, toolkit, project, ont, article, dbtoolkit, sentence
from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory, CachingMeta
import cachable
from functools import partial
import table3
from idlabel import IDLabel

def getCodedArticle(db, cjaid):
    data = db.doQuery("select codingjobid, setnr from codingjobs_articles where codingjob_articleid=%i"% cjaid)
    if not data: return None
    cjid, setnr = data[0]
    return Codingjob(db, cjid).getSet(setnr).getArticle(cjaid)
    
def getCodedArticleIdsFromArticleId(db, articleid):
    data = db.doQuery("select codingjob_articleid from codingjobs_articles where articleid=%i"% articleid)
    if not data: return []
    return (row[0] for row in data)

def getCodedArticlesFromArticleId(db, articleid):
    for cjaid in getCodedArticleIdsFromArticleId(db, articleid):
        yield getCodedArticle(db, cjaid)

def getCodedSentencesFromArticleId(db, articleid):
    for ca in getCodedArticlesFromArticleId(db, articleid):
        for cs in ca.sentences:
            yield cs

def getCodedArticlesFromCodingjobIds(db, codingjobids):
    return getCodedArticlesFromCodingjobs(map(partial(CodingJob, db), codingjobids))

def getCodedArticlesFromCodingjobs(codingjobs):
    for cj in codingjobs:
        for s in cj.sets:
            for ca in s.articles:
                yield ca
                    
def getCodedSentencesFromCodingjobIds(db, codingjobids):
    cjs =[Codingjob(db, id) for id in codingjobids]
    return getCodedSentencesFromCodingjobs(cjs)


def getCodedSentencesFromCodingjobs(codingjobs):
    toolkit.ticker.warn("Caching")
    cachable.cache(codingjobs, sets=dict(articles=dict(article=["sentences"], sentences=[])))
    toolkit.ticker.warn("Returning")
    for ca in getCodedArticlesFromCodingjobs(codingjobs):
        for cs in ca.sentences:
            yield cs
            
class CodingJob(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'codingjobs'
    __idcolumn__ = 'codingjobid'
    __dbproperties__ = ["name", "insertdate"]
    
    unitSchema = DBPropertyFactory("unitschemaid", dbfunc = lambda db, id: AnnotationSchema(db, id))
    articleSchema = DBPropertyFactory("articleschemaid", dbfunc = lambda db, id: AnnotationSchema(db, id))
    project = DBPropertyFactory("projectid", dbfunc = lambda db, id : project.Project(db, id))
    owner = DBPropertyFactory("owner_userid", dbfunc = lambda db, id : user.User(db, id))
    
    sets = DBFKPropertyFactory("codingjobs_sets", ["codingjobid", "setnr"], factory = lambda: CodingjobSet, uplink="job")
        
    def getLink(self):
        return "codingjobDetails?codingjobid=%i" % self.id

    def getSet(self, setnr):
        for set in self.sets:
            if set.setnr == setnr:
                return set

    def getAllCodedArticles(self):
        for s in self.sets:
            for ca in s.articles:
                yield ca
    
    def getNonCodedArticleids(self): # articlids that do not have any codings in this job
        sql = """
        select v.articleid
        from vw_codingjobs_articles_done as v
        where v.codingjobid = %d and v.has_arrow = 0 and v.has_artannot = 0 and (v.irrelevant IS NULL or v.irrelevant = 0)
        and not exists (
            select * from vw_codingjobs_articles_done as vw where vw.codingjobid = %d and vw.has_arrow > 0 and vw.has_artannot > 0 and vw.articleid = v.articleid
        )
        """ % (self.id, self.id)
        
        data = self.db.doQuery(sql)
        aids = [row[0] for row in data]
        return aids

    def findCodedArticles(self, art):
        if type(art) not in (tuple, set, list): art = [art]
        art = set((a if type(a)==int else a.id) for a in art)
        for cjs in self.sets:
            for ca in cjs.articles:
                if ca.article.id in art:
                    yield ca
    
    def findCodedArticle(self, art=None, coder=None, cjaid=None):
        if art and coder:
            for set in self.sets:
                if set.coder == coder:
                    for ca in set.articles:
                        if ca.article == art:
                            return ca
        elif cjaid:
            for set in self.sets:
                for ca in set.articles:
                    if ca.id == cjaid:
                        return ca
        else:
            raise Exception("Need either art and coder OR cjaid")

    def idname(self):
        return "%i - %s" % (self.id, self.name)

        
    def addSet(self, userid, aids):
        setnr = len(self.sets) + 1
        self.db.insert('codingjobs_sets', {'codingjobid':self.id, 'setnr': setnr, 'coder_userid' : userid}, 
                    retrieveIdent = False)
        for aid in aids:
            self.db.insert('codingjobs_articles', {'codingjobid' : self.id, 'setnr' : setnr, 'articleid' : aid}, 
                retrieveIdent = False)
        self.db.commit()
        
        
class CodedUnit(Cachable):
    def __init__(self, db, id, **cache):
        Cachable.__init__(self, db, id, **cache)
    def init(self, schema):
        self.annotationschema = schema
        self.fields = {} # fieldname : property
        for field in schema.fields:
            self.fields[field.fieldname] = self.addDBProperty(field.fieldname, func=field.deserialize, table=schema.table)

    @property
    def values(self):
        return self.fields
            
    def getValue(self, field):
        if isinstance(field, AnnotationSchemaField):
            field = field.fieldname
        if field not in self.fields: return None
        return self.fields[field].get()


    
                               

Codingjob = CodingJob

class CodedArticle(CodedUnit):
    __table__ = 'codingjobs_articles'
    __idcolumn__ = 'codingjob_articleid'
    __labelprop__ = None

    article = DBPropertyFactory("articleid", dbfunc = lambda db, id : article.Article(db, id))
    set = DBPropertyFactory(["codingjobid", "setnr"], dbfunc = lambda db, cjid, setnr : CodingjobSet(db, (cjid, setnr)))
    def __init__(self, db, id, **cache):
        CodedUnit.__init__(self, db, id, **cache)
        job = self.set.job
        self.init(job.articleSchema)
        self.addDBFKProperty("sentences", job.unitSchema.table, "arrowid",
                             function=lambda id : CodedSentence(self.db, id, job.unitSchema, ca=self))
        self.addDBProperty("confidence", table=job.articleSchema.table, func = lambda c : float(c) / 1000)
            
    def getArticle(self):
        return self.article

def getSentence(db, sid): return sentence.Sentence(db, sid)
        
class CodedSentence(CodedUnit):
    __idcolumn__ = 'arrowid'
    ca = DBPropertyFactory("codingjob_articleid", dbfunc=CodedArticle)
    sentence = DBPropertyFactory("sentenceid", dbfunc=getSentence)

    def __init__(self, db, id, schema, **cache):
        CodedUnit.__init__(self, db, id, **cache)
        self.init(schema)
        self.__table__ = schema.table

    def getFilter(self):
        return "arrowid", self.arrowid        
    def getArticle(self):
        return self.ca.article

getCodingJob = CodingJob

def getCodedArticle(db, cjaid):
    cjid = db.getValue("select codingjobid from codingjobs_articles where codingjob_articleid = %i"  % cjaid)
    job = getCodingJob(db, cjid)
    return job.findCodedArticle(cjaid = cjaid)

class CodingJobSet(Cachable):
    __table__ = 'codingjobs_sets'
    __idcolumn__ = ['codingjobid', 'setnr']
    __labelprop__ = None
    
    coder = DBPropertyFactory("coder_userid", dbfunc = lambda db,id : user.User(db, id))
    articles = DBFKPropertyFactory("codingjobs_articles", "codingjob_articleid", factory = lambda: CodedArticle, uplink="set")
    job = DBPropertyFactory("codingjobid", dbfunc = lambda db, id: CodingJob(db, id))
    def __init__(self, db, (jobid, setnr), **cache):
        Cachable.__init__(self, db, (jobid, setnr), **cache)
        self.setnr = setnr

    def getArticle(self, cjaid):
        for a in self.articles:
            if a.id == cjaid:
                return a

    def getArticles(self):
        cachable.cacheMultiple(self.articles, "article")
        return [a.article for a in self.articles]
    def getArticleIDS(self):
        return set(a.id for a in self.getArticles())

    def getNArticleCodings(self):
        SQL = """select count(*) from %s x
              inner join codingjobs_articles ca on x.codingjob_articleid = ca.codingjob_articleid
              where codingjobid = %d and setnr = %d""" % (self.job.articleSchema.table, self.job.id, self.setnr)
        return self.job.db.getValue(SQL)
        
    def getNUnitCodings(self):
        SQL = """select count(distinct articleid), count(*) from %s x
              inner join codingjobs_articles ca on x.codingjob_articleid = ca.codingjob_articleid
              where codingjobid = %d and setnr = %d""" % (self.job.unitSchema.table, self.job.id, self.setnr)
        return self.job.db.doQuery(SQL)[0]
    @property
    def label(self):
        return repr(self)
        
CodingjobSet = CodingJobSet

def paramdict(paramstr):
    d = {}
    if not paramstr: return d
    for kv in paramstr.split(","):
        k,v = kv.split("=")
        d[k.strip()] = v.strip()
    return d

class AnnotationSchema(Cachable):
    __idcolumn__ = 'annotationschemaid'
    __table__ = 'annotationschemas'
    __dbproperties__ = ["name", "articleschema"]
    __metaclass__ = CachingMeta
    params = DBPropertyFactory("params", func=paramdict)

    def __init__(self, db, id):
        Cachable.__init__(self, db, id)
        #todo naar class variables
        self.addDBProperty("table", "location", lambda loc : loc.split(":")[0])
        self.addDBFKProperty("fields", "annotationschemas_fields", ["fieldnr", "fieldname", "label", "fieldtypeid", "params", "deflt"], function=self.createField)

    def createField(self, fieldnr, fieldname, label, fieldtype, params, deflt):
        if fieldtype in (5,):
            return OntologyAnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
        elif fieldtype in (3,4,8):
            return LookupAnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
        elif fieldtype == 12:
            return FromAnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
        else:
            return AnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
    

    def getField(self, fieldname):
        for f in self.fields:
            if f.fieldname == fieldname: return f

    @property
    def language(self):
        return int(self.params.get("language", 1))

    def SQLSelect(self, extra = []):
        fields = extra + [f.fieldname for f in self.fields]
        return "select [%s] from %s " % ("],[".join(fields), self.table)

    def asDict(self, values):
        return dict(zip([f.fieldname for f in self.fields], values))

    def fieldNames(self):
        return (f.fieldname for f in self.fields)

    def cacheMany(self, units):
        cachable.cache(units, *self.fieldNames())
    
    def idname(self):
        return "%i - %s" % (self.id, self.name)

    def __hash__(self):
        return hash(self.id)
    def __eq__(self, other):
        return type(other) == AnnotationSchema and other.id == self.id

def getAnnotationschemas(db):
    """ Iterate over all annotation schema objects """
    ids = db.doQuery("SELECT annotationschemaid FROM annotationschemas")
    for a in ids:
        yield AnnotationSchema(db, a[0])


class AnnotationSchemaField(toolkit.IDLabel):
    def __init__(self, schema, fieldnr, fieldname, label, fieldtype, params, default):
        toolkit.IDLabel.__init__(self, (schema.id, fieldnr), label)
        self.schema = schema
        self.fieldnr = fieldnr
        self.fieldname = fieldname
        self.fieldtype = fieldtype
        self.params = paramdict(params)
        self.default = default
    def deserialize(self, value):
        return value
    def getLabel(self, value, annotation=None):
        if type(value) == float:
            return "%1.2f"  % value
        return value
    def getValue(self, unit):
        return unit.getValue(self)
    def hasLabel(self):
        return False
    def cache(self):
        pass

class LookupAnnotationSchemaField(AnnotationSchemaField):
    def __init__(self, *vals):
        AnnotationSchemaField.__init__(self, *vals)
        self._labels = None
    def deserialize(self, value):
        if value is None: return None
        label = self.getLabels().get(value, None)
        result = toolkit.IDLabel(value, label)
        return result
        # raise Exception([value, self.getLabels().get(value, None), self.getLabels()])
        #return LookupValue(value, self.getLabels().get(value, None))
    def hasLabel(self):
        return True
    def getLabels(self):
        if self._labels is None:
            if self.fieldtype == 4:
                self._labels = {}
                for i, val in enumerate(self.params['values'].split(";")):
                    if ":" in val:
                        i, val = val.split(":")
                        i = int(i)
                    self._labels[i] = val
            else:
                sql = "SELECT %s, %s FROM %s" % (self.params['key'], self.params['label'], self.params['table'])
                
                # BUG (see part of e-mail below).
                # 
                # [ e-mail]
                # ..certain countries/organizations (I suspect those that were added or changed
                # by the Swiss team) are still represented with an ID number instead of their name.
                # When the coders e.g. coded "NATO", AmCAT shows "IDLabel(282)".
                #
                # To a similar extent, for the variables "actor1-3", "mp1-3", and "canton1-3",
                # AmCAT only rarely shows labels. Most of the annotations appear in the form "IDLabel(63)"
                # (standing here for what the coder wanted to be "206 Delamuraz Jean-Pascal").
                # [/ e-mail ]
                #
                # This is probably causes by iNet, which doesn't select id fields (206) but a row
                # number (63).
                
                result = self.schema.db.doQuery(sql)
                self._labels = dict((k,v.decode('latin-1')) for k,v in result)
                #self._labels = {}
                #for i in xrange(len(result)):
                #    self._labels[i] = result[i][1]
                
        return self._labels
    def getLabel(self, value, annotation=None):
        if value is None: return None
        if type(value) in (int, float, str, unicode):
            return str(value)
        return value.label
        #v = self.deserialize(value)
        #if not v: return None
        #return "@@ %r / %r / %r / %r $$" % (value, v, v.id, v.label)
        #return v.label
    def cache(self):
        self.getLabels()
        
        
class LookupValue(toolkit.IDLabel):
    pass

class FromAnnotationSchemaField(AnnotationSchemaField):
    def __init__(self, *vals):
        AnnotationSchemaField.__init__(self, *vals)
    def getLabel(self, value, codedsentence=None):
        froms = []
        for s in codedsentence.ca.sentences:
            if s.sentence == codedsentence.sentence:
                val = s.getValue(self.fieldname)
                if not val: val = 0
                froms.append(val)
        froms.sort()
        if not value: value = 0
        i = froms.index(value)
        
        if i == len(froms)-1: to = None
        else: to = froms[i+1]

        return " ".join(codedsentence.sentence.text.split()[value:to])

    def hasLabel(self):
        return True
        
        
class OntologyAnnotationSchemaField(AnnotationSchemaField):
    def __init__(self, *vals):
        AnnotationSchemaField.__init__(self, *vals)
        self._set = None
    def deserialize(self, value):
        if value is None: return None
        return ont.Object(self.schema.db, value, languageid=self.schema.language)
    @property
    def set(self):
        if self._set is None:
            setid = self.params.get("setid")
            if not setid: setid = self.params.get("set")
            if not setid: setid = self.params.get("sets")
            if not setid:
                toolkit.warn("OntologyASF without setid? %s" % (self.params))
                return None
            self._set = ont.Set(self.schema.db, int(setid))
        return self._set
    def getLabel(self, value, codedsentence=None):
        v = self.deserialize(value)
       
        if not v: return None
        try:
            return v.getLabel()
        except AttributeError:
            return v
    def hasLabel(self):
        return True
    def cache(self):
        self.set.cacheLabels()

def getCAJobs(cas):
    return sorted(set([ca.set.job for ca in cas]))
def getCACoders(cas):
    return sorted(set(ca.set.coder for ca in cas))


def getValue(row, schemafield):
    val = row.getValue(schemafield)
    val = schemafield.deserialize(val)
    return val

def getCodingTable(units, valfunc=getValue, coder=True):
    units.sort(key = lambda r:(r.ca.set.coder, r.sentence))
    t = table2.ObjectTable(rows=units)
    t.addColumn("Coder", lambda r: r.ca.set.coder)
    t.addColumn("Sentence", lambda r: "%i.%i : %s" % (r.sentence.parnr, r.sentence.sentnr, r.sentence.text[:20]))
    for c in units[0].ca.set.job.unitSchema.fields:
        t.addColumn(c.label, functools.partial(valfunc, schemafield=c))
    return t

def countUnits(jobs, field=None):
    if not toolkit.isSequence(jobs): jobs = [jobs]
    tot, coded = 0,0
    for job in jobs:
        for ca in job.getAllCodedArticles():
            tot += 1
            values = ca.getValueObject(field) if field else ca.values
            if values is not None: coded += 1
    return tot, coded


def getk06CodedSentences(db):
    SQL = """select codingjob_articleid from codingjobs_groups g inner join codingjobs_articles a on g.codingjobid = a.codingjobid
             where normative=1 and g.groupid=1"""
    for cjaid, in db.doQuery(SQL):
        ca = CodedArticle(db, cjaid)
        for cs in ca.sentences:
            yield cs
    
def getFieldType(field):
    if type(field) in (OntologyAnnotationSchemaField, LookupAnnotationSchemaField):
        return IDLabel
    elif field.fieldtype in (6,9):
        return float
    elif field.fieldtype in (2,):
        return int
    return str

def getValue(unit, field):
    if unit is None: return None
    return unit.getValue(field.fieldname)

class FieldColumn(table3.ObjectColumn):
    def __init__(self, field, article):
        table3.ObjectColumn.__init__(self, field.label, fieldname=field.fieldname, fieldtype=getFieldType(field))
        self.field = field
        self.article = article
        self.valuelabels = {}
    def getUnit(self, row):
        return row.ca if self.article else row.cs
    def getCell(self, row):
        val = getValue(self.getUnit(row), self.field)
        
        return val

def createCodingJob(project, name, unitschema, articleschema, coders=[]):
    if not type(unitschema) == int: unitschema = unitschema.id
    if not type(articleschema) == int: articleschema = articleschema.id
    cjid = project.db.insert("codingjobs", dict(projectid=project.id, unitschemaid=unitschema, articleschemaid=articleschema, name=name))
    for i, coder in enumerate(coders):
        if not type(coder) == int: coder = coder.id
        project.db.insert("codingjobs_sets", dict(codingjobid=cjid, setnr=i+1, coder_userid=coder), retrieveIdent=False)
    return CodingJob(project.db, cjid, project=project)

def cloneCodingJob(codingjob, newname = None, coders=[]):
    if newname is None: newname = "%s (kopie)" % (codingjob.label,)
    return createCodingJob(codingjob.project, newname, codingjob.unitSchema, codingjob.articleSchema, coders=coders)
    
def createCodedArticle(codingjobset, article):
    cjid, setnr = codingjobset.id
    if not type(article) == int: article = article.id 
    cjaid = codingjobset.db.insert("codingjobs_articles", dict(codingjobid=cjid, setnr=setnr, articleid=article))
    return CodedArticle(codingjobset.db, cjaid)
    
if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True)

    cj = CodingJob(db, 423)
    cj2 = cloneCodingJob(cj, "test", [2])
    print `cj2`, cj2
    db.commit()
