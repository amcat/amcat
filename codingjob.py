import user, toolkit, project

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


class CodingjobSet(object):
    def __init__(self, job, setnr):
        self.job = job
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
            SQL = "select articleid from codingjobs_articles where %s" % self._where
            self._articles = [self.job.db.article(aid) for (aid,) in self.job.db.doQuery(SQL)]
        return self._articles
    _articles = None

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
    def fields(self):
        if self._fields is None:
            self._fields = []
            SQL = """select fieldnr, fieldname, label, fieldtypeid, params
            from annotationschemas_fields where annotationschemaid=%i
            order by fieldnr""" % self.id
            for vals in self.db.doQuery(SQL):
                self._fields.append(AnnotationSchemaField(self, *vals))
        return self._fields
    _fields = None
                                    

    def idname(self):
        return "%i - %s" % (self.id, self.name)
            
def paramdict(paramstr):
    d = {}
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
                                        
        return self._labels.get(value, value)
        
                

