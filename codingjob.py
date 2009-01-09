import user, toolkit, project, ontology
from toolkit import cached

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
    def sets(self):
        if self._sets is None:
            self._sets = {}
            SQL = "select setnr from codingjobs_sets where codingjobid=%i" % self.id
            self._sets = [CodingjobSet(self, setnr) for (setnr,) in  self.db.doQuery(SQL)]
        return self._sets
    _sets = None

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

    def idname(self):
        return "%i - %s" % (self.id, self.name)


class CodedArticle(object):
    def __init__(self, set, cjaid, aid):
        self.set = set
        self.cjaid = cjaid
        self.aid = aid
        self.db = set.db

    @property
    def article(self):
        if self._article is None:
            self._article = self.db.article(self.aid)
        return self._article
    _article = None

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
        fields = [f.fieldname for f in schema.fields]
        SQL = "select %s from %s where codingjob_articleid = %i" % (",".join(fields), schema.table, self.cjaid)
        data = self.db.doQuery(SQL)
        if data:
            return dict(zip(fields, data[0]))
        else:
            return None

    def getValue(self, field):
        if self.values is None: return None
        return self.values.get(field.fieldname, None)
        
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
        fields = list(f.fieldname for f in schema.fields)
        SQL = "select %s from %s where arrowid = %i" % (",".join(fields), schema.table, self.arrowid)
        return dict(zip(fields, self.db.doQuery(SQL)[0]))

    def getValue(self, field):
        if type(field) == AnnotationSchemaField:
            field = field.fieldname
        return self.values.get(field, None)

class CodingjobSet(object):
    def __init__(self, job, setnr):
        self.job = job
        self.db = job.db
        self.setnr = setnr
        self._articles = None
        self._where = "codingjobid = %i and setnr = %i" % (self.job.id, self.setnr)
        
    @property
    def coder(self):
        if self._coder is None:
            SQL = "select coder_userid from codingjobs_sets where %s" % self._where
            self._coder = self.job.db.users.getUser(self.job.db.getValue(SQL))
        return self._coder
    _coder = None

    @property
    def articles(self):
        if self._articles is None:
            SQL = "select codingjob_articleid, articleid from codingjobs_articles where %s" % self._where
            self._articles = [CodedArticle(self, *data) for data in self.job.db.doQuery(SQL)]
        return self._articles
    _articles = None

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
        return [AnnotationSchemaField(self, *vals) for vals in self.db.doQuery(SQL)]

    def getField(self, fieldname):
        for f in self.fields:
            if f.fieldname == fieldname: return f
                                    
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
        self._labels = None

    def hasLabel(self):
        return self.fieldtype in (3,4,5,8)

    def getLabel(self, value):
        if self._labels is None:
            self._labels = {}
            if self.fieldtype == 4:
                vals = self.params['values']
                for i, val in enumerate(vals.split(";")):
                    if ":" in val:
                        i, val = val.split(":")
                        i = int(i)
                    self._labels[i] = val
            elif self.fieldtype in (3, 8):
                #table=net_arrowtypes,key=arrowtypeid,label=name
                #table=dnn_vw_katernenperkrant,key=katernid,label=label
                table = self.params['table']
                key = self.params['key']
                label = self.params['label']
                sql = "SELECT %s, %s FROM %s" % (key, label, table)
                for k, l in self.schema.db.doQuery(sql):
                    self._labels[k] = l
            elif self.fieldtype == 5:
                ids = self.params.get('ids', None)
                if not ids: ids = self.params['ontologyid']
                sql = "select objectid, label from ont_objects where ontologyid in (%s)" % ids.replace(";",",")
                for k, l in self.schema.db.doQuery(sql):
                    self._labels[k] = l
                                        
        return self._labels.get(value, None)
        
                

    def __hash__(self):
        return hash(self.schema) ^ hash(self.fieldnr)
    def __eq__(self, other):
        return type(other) == AnnotationSchemaField and self.schema == other.schema and self.fieldnr == other.fieldnr
    
