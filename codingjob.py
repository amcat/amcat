import user, toolkit, project, ontology, article
from toolkit import cached

def getCodedArticle(db, cjaid):
    data = db.doQuery("select codingjobid, setnr from codingjobs_articles where codingjob_articleid=%i"% cjaid)
    if not data: return None
    cjid, setnr = data[0]
    return Codingjob(db, cjid).getSet(setnr).getArticle(cjaid)
    

class Codingjob(object):

    def __init__(self, db, id):
        self.db = db
        self.id = id
        
    def _getFields(self):
        SQL = """select name, unitschemaid, articleschemaid, params, owner_userid, insertdate, projectid from codingjobs
              where codingjobid=%i"""%self.id
        if self._fields: return
        self._name, ua, aa, self._params, ownerid, insertdate, projectid = self.db.doQuery(SQL)[0]
        self._unitschema = AnnotationSchema(self.db, ua)
        self._artschema = AnnotationSchema(self.db, aa)
        self._owner = self.db.users.getUser(ownerid)
        self._project = project.Project(self.db, projectid)
        self._insertdate = insertdate
        self._fields = True
    _fields = False

    def getLink(self):
        return "codingjobDetails?codingjobid=%i" % self.id

    @property
    def name(self):
        self._getFields()
        return self._name

    @property
    def articleSchema(self):
        self._getFields()
        return self._artschema

    @property
    def unitSchema(self):
        self._getFields()
        return self._unitschema

    @property
    @cached
    def sets(self):
        SQL = "select setnr from codingjobs_sets where codingjobid=%i" % self.id
        return [CodingjobSet(self, setnr) for (setnr,) in  self.db.doQuery(SQL)]

    @property
    def owner(self):
        self._getFields()
        return self._owner
            
    @property
    def insertdate(self):
        self._getFields()
        return self._insertdate

    @property
    def project(self):
        self._getFields()
        return self._project
    
    def getSet(self, setnr):
        for set in self.sets:
            if set.setnr == setnr:
                return set

    def findCodedArticle(self, art, coder):
        for set in self.sets:
            if set.coder == coder:
                for ca in set.articles:
                    if ca.article == art:
                        return ca

    def idname(self):
        return "%i - %s" % (self.id, self.name)

    def cacheValues(self, artannots = False, arrows = False, sentences = False, headlines=True):
        #nog mogelijke optimalisaties:
        # categorize 1x ophalen voor meer objecten
        # niet alle sentences ophalen (maar lastig om verwacht gedrag article.sentences niet te breken...)
        
        # cache article-level values if needed
        # do this first to allow caching (null) values for articles without annotations
        if artannots:
            aavalues = {}
            SQL = self.articleSchema.SQLSelect(extra=["codingjob_articleid"])
            SQL += " WHERE codingjob_articleid in (select codingjob_articleid from codingjobs_articles where codingjobid=%i)" % (self.id)
            for row in self.db.doQuery(SQL):
                cjaid = row[0]
                row = row[1:]
                aavalues[cjaid] = row

        #create articles
        ids = "select articleid from codingjobs_articles where codingjobid=%i" % (self.id,)
        articles = {}
        for a in article.articlesFromDB(self.db, ids, headline=headlines):
            articles[a.id] = a

        # create sets and codedarticles
        SQL = """select setnr, codingjob_articleid, articleid
        from codingjobs_articles where codingjobid=%i""" % self.id
        sets = []
        setsbynr = {}
        articlesperset = {}
        codedarticles = {}
        csperca = {}
        for setnr, cjaid, aid in self.db.doQuery(SQL):
            if setnr in setsbynr:
                s = setsbynr[setnr]
            else:
                s = CodingjobSet(self, setnr)
                sets.append(s)
                setsbynr[setnr] = s
                a = []
                articlesperset[setnr] = a
                toolkit.setCachedProp(s, "articles", a)

            ca = CodedArticle(s, cjaid, aid)
            articlesperset[setnr].append(ca)
            codedarticles[cjaid] = ca
            toolkit.setCachedProp(ca, "article", articles[aid])
            cs = []
            csperca[ca] = cs
            toolkit.setCachedProp(ca, "sentences", cs)
            
            if artannots:
                values = aavalues.get(cjaid, None)
                if values: values = self.articleSchema.asDict(values)
                toolkit.setCachedProp(ca, "values", values)

        if arrows:
            #create sentences
            sentsperart = {}
            sents = {}
            SQL = """select articleid, sentenceid, parnr, sentnr from sentences s
                     where articleid in (select articleid from codingjobs_articles where codingjobid = %i)""" % (self.id,)
            for aid, sid, parnr, sentnr in self.db.doQuery(SQL):
                a = articles[aid]
                if not a in sentsperart:
                    l = []
                    sentsperart[a] = l
                    toolkit.setCachedProp(a, "sentences", l)
                s = article.Sentence(a, sid, parnr, sentnr)
                sents[sid] = s
                sentsperart[a].append(s)
            
            SQL = self.unitSchema.SQLSelect(extra=["arrowid","codingjob_articleid", "sentenceid"])
            SQL += " WHERE codingjob_articleid in (select codingjob_articleid from codingjobs_articles where codingjobid=%i)" % (self.id)
            for row in self.db.doQuery(SQL):
                arrowid, cjaid, sid = row[:3]
                row = row[3:]
                ca = codedarticles[cjaid]
                sent = sents[sid]
                cs = CodedSentence(ca, arrowid, sent)
                values = self.unitSchema.asDict(row)
                toolkit.setCachedProp(cs, "values", values)
                csperca[ca].append(cs)

            if sentences:
                #cache sentences for articles with arrows
                SQL = """select sentenceid, isnull(longsentence, sentence), encoding from sentences
                where sentenceid in (select sentenceid from net_arrows r inner join codingjobs_articles a on r.codingjob_articleid = a.codingjob_articleid
                                     where codingjobid=%i)""" % self.id
                for sid, sent, encoding in self.db.doQuery(SQL):
                    text = article.decode(sent, encoding)
                    toolkit.setCachedProp(sents[sid], "text", text)
                    
                                                

        toolkit.setCachedProp(self, "sets", sets)
        

class CodedArticle(object):
    def __init__(self, set, cjaid, aid):
        self.set = set
        self.cjaid = cjaid
        self.aid = aid
        self.db = set.db

    @property
    @cached
    def article(self):
        return self.db.article(self.aid)

    @property
    @cached
    def sentences(self):
        SQL = ("select arrowid, sentenceid from %s where codingjob_articleid = %i"
               % (self.set.job.unitSchema.table, self.cjaid))    
        return [CodedSentence(self, id, self.getSentence(sid)) for (id,sid) in self.set.job.db.doQuery(SQL)]

    def getSentence(self, sid):
        for s in self.article.sentences:
            if s.sid == sid:
                return s
        raise Exception("Cannot find sentence %i in article %i" % (sid, self.article.id))

    @property
    @cached
    def values(self):
        schema = self.set.job.articleSchema
        SQL = schema.SQLSelect() + " where codingjob_articleid = %i" % self.cjaid
        data = self.db.doQuery(SQL)
        if data: return schema.asDict(data[0])
        else: return None

    def getValue(self, field):
        if self.values is None: return None
        if isinstance(field, AnnotationSchemaField):
            field = field.fieldname
        return self.values.get(field, None)
        
class CodedSentence(object):
    def __init__(self, codedArticle, arrowid, sentence):
        self.arrowid = arrowid
        self.ca = codedArticle
        self.db = self.ca.db
        self.sentence = sentence

    @property
    @cached
    def values(self):
        schema = self.ca.set.job.unitSchema
        SQL = schema.SQLSelect() + " where arrowid = %i" % (self.arrowid,)
        return schema.asDict(self.db.doQuery(SQL)[0])

    def getValue(self, field):
        if isinstance(field, AnnotationSchemaField):
            field = field.fieldname
        return self.values.get(field, None)

class CodingjobSet(object):
    def __init__(self, job, setnr):
        self.job = job
        self.db = job.db
        self.setnr = setnr
        self._where = "codingjobid = %i and setnr = %i" % (self.job.id, self.setnr)
        
    @property
    @cached
    def coder(self):
        SQL = "select coder_userid from codingjobs_sets where %s" % self._where
        return self.job.db.users.getUser(self.job.db.getValue(SQL))

    @property
    @cached
    def articles(self):
        SQL = "select codingjob_articleid, articleid from codingjobs_articles where %s" % self._where
        return [CodedArticle(self, *data) for data in self.job.db.doQuery(SQL)]

    def getArticle(self, cjaid):
        for a in self.articles:
            if a.cjaid == cjaid:
                return a

    def getArticleIDS(self):
        return set([a.article.id for a in self.articles])

    def getNArticleCodings(self):
        SQL = """select count(*) from %s x
              inner join codingjobs_articles ca on x.codingjob_articleid = ca.codingjob_articleid
              where %s""" % (self.job.articleSchema.table, self._where)
        return self.job.db.getValue(SQL)
        
    def getNUnitCodings(self):
        SQL = """select count(distinct articleid), count(*) from %s x
              inner join codingjobs_articles ca on x.codingjob_articleid = ca.codingjob_articleid
              where %s""" % (self.job.unitSchema.table, self._where)
        return self.job.db.doQuery(SQL)[0]

        

class AnnotationSchema(object):

    def __init__(self, db, id):
        self.db = db
        self.id = id

    def _getInfo(self):
        if self._info: return
        SQL = """select name, location, articleschema, params from annotationschemas
              where annotationschemaid=%i""" % self.id
        self._name, loc, self._articleschema, self._params = self.db.doQuery(SQL)[0]
        self._table = loc.split(":")[0]
        self._info = True
    _info = False

    @property
    def table(self):
        self._getInfo()
        return self._table

    @property
    def name(self):
        self._getInfo()
        return self._name

    @property
    @cached
    def fields(self):
        SQL = """select fieldnr, fieldname, label, fieldtypeid, params
        from annotationschemas_fields where annotationschemaid=%i
        order by fieldnr""" % self.id
        ont = ontology.fromDB(self.db)
        return [getField(self, ont, *vals) for vals in self.db.doQuery(SQL)]

    def getField(self, fieldname):
        for f in self.fields:
            if f.fieldname == fieldname: return f

    def SQLSelect(self, extra = []):
        fields = extra + [f.fieldname for f in self.fields]
        return "select %s from %s " % (",".join(fields), self.table)

    def asDict(self, values):
        return dict(zip([f.fieldname for f in self.fields], values))
                                    
    def idname(self):
        return "%i - %s" % (self.id, self.name)

    def __hash__(self):
        return hash(self.id)
    def __eq__(self, other):
        return type(other) == AnnotationSchema and other.id == self.id
            
def paramdict(paramstr):
    d = {}
    if not paramstr: return d
    for kv in paramstr.split(","):
        k,v = kv.split("=")
        d[k] = v
    return d

class AnnotationSchemaField(object):
    def __init__(self, schema, fieldnr, fieldname, label, fieldtype, params):
        self.schema = schema
        self.fieldnr = fieldnr
        self.fieldname = fieldname
        self.label = label
        self.fieldtype = fieldtype
        self.params = paramdict(params)
    def deserialize(self, value):
        return value
    def getLabel(self, value):
        if type(value) == float:
            return "%1.2f"  % value
        return value
    def hasLabel(self):
        return False
    def __hash__(self):
        return hash(self.schema) ^ hash(self.fieldnr)
    def __eq__(self, other):
        try:
            return self.schema == other.schema and self.fieldnr == other.fieldnr
        except AttributeError, e:
            return False

class LookupAnnotationSchemaField(AnnotationSchemaField):
    def __init__(self, *vals):
        AnnotationSchemaField.__init__(self, *vals)
    def deserialize(self, value):
        if value is None: return None
        return LookupValue(value, self.labels.get(value, None))
    def hasLabel(self):
        return True
    @property
    @cached
    def labels(self):
        if self.fieldtype == 4:
            labels = {}
            for i, val in enumerate(self.params['values'].split(";")):
                if ":" in val:
                    i, val = val.split(":")
                    i = int(i)
                labels[i] = val
            return labels
        else:
            sql = "SELECT %(key)s, %(label)s FROM %(table)s" % self.params
            return dict(self.schema.db.doQuery(sql))
    def getLabel(self, value):
        v = self.deserialize(value)
        if not v: return None
        return v.label
class LookupValue(object):
    def __init__(self, id, label):
        self.id = id
        self.label = label
        
class OntologyAnnotationSchemaField(AnnotationSchemaField):
    def __init__(self, ont, *vals):
        AnnotationSchemaField.__init__(self, *vals)
        self.ont = ont
    def deserialize(self, value):
        if value is None: return None
        return self.ont.nodes[value]
    def getLabel(self, value):
        v = self.deserialize(value)
        if not v: return None
        return v.label
    def hasLabel(self):
        return True

def getField(schema, ont, fieldnr, fieldname, label, fieldtype, params):
    if fieldtype in (5,):
        return OntologyAnnotationSchemaField(ont, schema, fieldnr, fieldname, label, fieldtype, params)
    if fieldtype in (3,4,8):
        return LookupAnnotationSchemaField(schema, fieldnr, fieldname, label, fieldtype, params)
    else:
        return AnnotationSchemaField(schema, fieldnr, fieldname, label, fieldtype, params)
    

