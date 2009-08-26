import user, toolkit, project, ont2, article, dbtoolkit
from cachable import Cachable
from functools import partial

def getCodedArticle(db, cjaid):
    data = db.doQuery("select codingjobid, setnr from codingjobs_articles where codingjob_articleid=%i"% cjaid)
    if not data: return None
    cjid, setnr = data[0]
    return Codingjob(db, cjid).getSet(setnr).getArticle(cjaid)
    
def getCodedArticleIdsFromArticleId(db, articleid):
    data = db.doQuery("select codingjob_articleid from codingjobs_articles where articleid=%i"% articleid)
    if not data: return None
    return (row[0] for row in data)
    

class Codingjob(Cachable):
    __table__ = 'codingjobs'
    __idcolumn__ = 'codingjobid'
    def __init__(self, db, id):
        Cachable.__init__(self, db, id)
        for prop, field, func in (
            ("name", None, None),
            ("insertdate", None, None),
            ("unitSchema", "unitschemaid", partial(AnnotationSchema, self.db)),
            ("articleSchema", "articleschemaid", partial(AnnotationSchema, self.db)),
            ("project", "projectid", partial(project.Project, self.db)),
            ("owner", "owner_userid", self.db.users.getUser)):
            self.addDBProperty(prop, field, func)
        self.addDBFKProperty("sets", "codingjobs_sets", "setnr", function=partial(CodingjobSet, self))
        
    def getLink(self):
        return "codingjobDetails?codingjobid=%i" % self.id

    def getSet(self, setnr):
        for set in self.sets:
            if set.setnr == setnr:
                return set

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
                    if ca.cjaid == cjaid:
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
        
        
        
    def cacheValues(self, artannots = False, arrows = False, sentences = False, headlines=True):
        return
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
            data = list(self.db.doQuery(SQL))
            for aid, sid, parnr, sentnr in data:
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
                    text = dbtoolkit.decode(sent, encoding)
                    toolkit.setCachedProp(sents[sid], "text", text)
                    
                                                

        toolkit.setCachedProp(self, "sets", sets)
        

class CodedArticle(Cachable):
    __table__ = 'codingjobs_articles'
    __idcolumn__ = 'codingjob_articleid'
    def __init__(self, set, cjaid, aid=None):
        Cachable.__init__(self, set.db, cjaid)
        self.cjaid = cjaid
        self.set = set
        self.addDBProperty("aid", "articleid")
        if aid: self.cacheValues(aid=aid)
        self.addFunctionProperty("article", lambda : self.db.article(self.aid))
        self.addFunctionProperty("values", self.getValues)
        self.addDBFKProperty("sentences", self.set.job.unitSchema.table, ["arrowid", "sentenceid"],
                             function=lambda id, sid : CodedSentence(self, id, self.getSentence(sid)))

    def getSentence(self, sid):
        for s in self.article.sentences:
            if s.sid == sid:
                return s
        raise Exception("Cannot find sentence %i in article %i" % (sid, self.article.id))

    def getValues(self):
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
    def __str__(self):
        return "Article %s coded by %s" % (self.article, self.set.coder)
    
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

_cache = {}
def getCodingJob(db, cjid):
    if (db, cjid) not in _cache:
        _cache[db, cjid] = Codingjob(db, cjid)
    return _cache[db, cjid]
        
    

def getCodedArticle(db, cjaid):
    cjid = db.getValue("select codingjobid from codingjobs_articles where codingjob_articleid = %i"  % cjaid)
    job = getCodingJob(db, cjid)
    return job.findCodedArticle(cjaid = cjaid)

class CodingjobSet(Cachable):
    __table__ = 'codingjobs_sets'
    __idcolumn__ = ['codingjobid', 'setnr']
    
    def __init__(self, job, setnr):
        Cachable.__init__(self, job.db, (job.id, setnr))
        self.job = job
        self.setnr = setnr
        self.addDBProperty("coder", "coder_userid", self.db.users.getUser)
        self.addDBFKProperty("articles", "codingjobs_articles", "codingjob_articleid", function=partial(CodedArticle, self))

    def getArticle(self, cjaid):
        for a in self.articles:
            if a.cjaid == cjaid:
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

class AnnotationSchemaField(object):
    def __init__(self, schema, fieldnr, fieldname, label, fieldtype, params, default):
        self.schema = schema
        self.fieldnr = fieldnr
        self.fieldname = fieldname
        self.label = label
        self.fieldtype = fieldtype
        self.params = paramdict(params)
        self.default = default
    def deserialize(self, value):
        return value
    def getLabel(self, value, annotation):
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
    def getLabel(self, value, annotation):
        if value is None: return None
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
    def getLabel(self, value, codedsentence):
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
    def getLabel(self, value, codedsentence):
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



if __name__ == '__main__':
    import dbtoolkit, adapter
    db = dbtoolkit.amcatDB()
    cj = Codingjob(db, 1859)
    print adapter.getLabel(cj, strict=True), cj.unitSchema
    set = list(cj.sets)[0]
    print set, set.coder
    for art in list(set.articles)[:5]:
        print art, art.cjaid, art.article.headline
        for sent in list(art.sentences)[:2]:
            print sent.id, sent.sentence
    
