import user, toolkit, project, ont2, article, dbtoolkit
from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory
from functools import partial

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
    for ca in getCodedArticlesFromCodingjobIds(db, codingjobids):
        for cs in ca.sentences:
            yield cs
            
class CodingJob(Cachable):
    __table__ = 'codingjobs'
    __idcolumn__ = 'codingjobid'
    __cacheme__ = True
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

    def findCodedArticles(self, art=None, coder=None):
        raise Exception([art, coder])
        for set in self.sets:
            if coder and set.coder <> coder: continue
            for ca in set.articles:
                if art and ca.article <> art: continue
                yield ca

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
        
        
Codingjob = CodingJob
        
class CodedArticle(Cachable):
    __table__ = 'codingjobs_articles'
    __idcolumn__ = 'codingjob_articleid'
    __labelprop__ = None

    article = DBPropertyFactory("articleid", dbfunc = lambda db, id : article.Article(db, id))
    set = DBPropertyFactory(["codingjobid", "setnr"], dbfunc = lambda db, cjid, setnr : CodingjobSet(db, (cjid, setnr)))
    def __init__(self, db, id, **cache):
        Cachable.__init__(self, db, id, **cache)
        self.schema =  self.set.job.articleSchema
        self.addDBFKProperty("sentences", self.set.job.unitSchema.table, ["arrowid", "sentenceid"],
                             function=lambda id, sid : CodedSentence(self, id, self.getSentence(sid)))
        for field in self.schema.fields:
            self.addDBProperty(field.fieldname, table=self.schema.table, func=field.deserialize)
        self.addFunctionProperty("values", self.getValues)
    def getSentence(self, sid):
        for s in self.article.sentences:
            if s.id == sid:
                return s
        raise Exception("Cannot find sentence %i in article %i" % (sid, self.article.id))

    def getValues(self):
        SQL = self.schema.SQLSelect() + " where codingjob_articleid = %i" % self.id
        data = self.db.doQuery(SQL)
        if data: return self.schema.asDict(data[0])
        else: return None

    def getValue(self, field):
        if self.values is None: return None
        if isinstance(field, AnnotationSchemaField):
            field = field.fieldname
        return self.values.get(field, None)
    def getValueObject(self, field):
        if isinstance(field, AnnotationSchemaField):
            field = field.fieldname
        return self.__getattribute__(field)

    
class CodedSentence(Cachable):
    def __init__(self, codedArticle, arrowid, sentence):
        Cachable.__init__(self, codedArticle.db, arrowid)
        self.arrowid = arrowid
        self.ca = codedArticle
        self.sentence = sentence
        self.addFunctionProperty("values", self.getValues)

    def getValues(self):
        schema = self.ca.set.job.unitSchema
        SQL = schema.SQLSelect() + " where arrowid = %i" % (self.arrowid,)
        return schema.asDict(self.db.doQuery(SQL)[0])

    def getValue(self, field):
        if isinstance(field, AnnotationSchemaField):
            field = field.fieldname
        return self.values.get(field, None)
        
    def getLink(self):
        return 'sentenceDetails?sentenceid=%d' % self.sentence.id

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

    def getArticleIDS(self):
        return set([a.article.id for a in self.articles])

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

CodingjobSet = CodingJobSet

class AnnotationSchema(Cachable):
    __idcolumn__ = 'annotationschemaid'
    __table__ = 'annotationschemas'
    
    def __init__(self, db, id):
        Cachable.__init__(self, db, id)
        self.ont = ont2.getOntology(self.db)
        self.addDBProperty("table", "location", lambda loc : loc.split(":")[0])
        self.addDBProperty("name")
        self.addDBProperty("articleschema")
        self.addDBFKProperty("fields", "annotationschemas_fields", ["fieldnr", "fieldname", "label", "fieldtypeid", "params", "deflt"], function=self.createField)

    def createField(self, fieldnr, fieldname, label, fieldtype, params, deflt):
        if fieldtype in (5,):
            return OntologyAnnotationSchemaField(self.ont, self, fieldnr, fieldname, label, fieldtype, params, deflt)
        elif fieldtype in (3,4,8):
            return LookupAnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
        elif fieldtype == 12:
            return FromAnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
        else:
            return AnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
    

    def getField(self, fieldname):
        for f in self.fields:
            if f.fieldname == fieldname: return f

    def SQLSelect(self, extra = []):
        fields = extra + [f.fieldname for f in self.fields]
        return "select [%s] from %s " % ("],[".join(fields), self.table)

    def asDict(self, values):
        return dict(zip([f.fieldname for f in self.fields], values))
                                    
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

def paramdict(paramstr):
    d = {}
    if not paramstr: return d
    for kv in paramstr.split(","):
        k,v = kv.split("=")
        d[k.strip()] = v.strip()
    return d

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
    def hasLabel(self):
        return False

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
                self._labels =  dict(self.schema.db.doQuery(sql))
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
    def __init__(self, ont, *vals):
        AnnotationSchemaField.__init__(self, *vals)
        self.ont = ont
    def deserialize(self, value):
        if value is None: return None
        val = self.ont.nodes.get(value)
        if val is None:
            return value
        return val
    def getLabel(self, value, codedsentence=None):
        v = self.deserialize(value)
       
        if not v: return None
        try:
            return v.getLabel()
        except AttributeError:
            return v
    def hasLabel(self):
        return True

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

if __name__ == '__main__':
    import dbtoolkit, adapter
    db = dbtoolkit.amcatDB()
    cj = Codingjob(db, 1859)
    print cj.label
    print cj.unitSchema
    print "----------"
    set = list(cj.sets)[0]
    print set, set.coder
    print set.job
    print set.job is cj

    art = list(set.articles)[0]
    print `art`
    print `art.set`
    print art.set.coder
    print art.article
    print art.set is set
    
    
