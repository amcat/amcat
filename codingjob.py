import user, toolkit, project, ont, article, dbtoolkit, sentence

from cachable2 import Cachable, DBProperty, ForeignKey, DBProperties

from functools import partial
import table3
from idlabel import IDLabel
import annotationschema

import logging; log = logging.getLogger(__name__)
#import amcatlogging; amcatlogging.debugModule()

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
    __table__ = 'codingjobs'
    __idcolumn__ = 'codingjobid'
    __labelprop__ = 'name'
    name, insertdate = DBProperties(2)

    unitSchema = DBProperty(annotationschema.AnnotationSchema, getcolumn="unitschemaid")
    articleSchema = DBProperty(annotationschema.AnnotationSchema, getcolumn="articleschemaid")
    project = DBProperty(lambda:project.Project)
    owner = DBProperty(lambda:user.User, getcolumn="owner_userid")

    sets = ForeignKey(lambda:CodingJobSet, includeOwnID=True)
        
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
Codingjob = CodingJob

class CodingJobSet(Cachable):
    __table__ = 'codingjobs_sets'
    __idcolumn__ = ['codingjobid', 'setnr']
    
    coder = DBProperty(lambda:user.User, getcolumn="coder_userid")
    articles = ForeignKey(lambda:CodedArticle)

    @property
    def job(self):
        return CodingJob(self.db, self.jobid)
    @property
    def setnr(self):
        return self.id[1]
    @property
    def jobid(self):
        return self.id[0]

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
        
class CodedUnit(object):
    def __init__(self):
        self._fields = None
        self._values = {}
        
    def __getattr__(self, attr):
        # if not found, check fields
        if attr.startswith("_"): return super(CodedUnit, self).__getattribute__(attr)
        log.debug("__getattr__(%r), in fields %s?" % (attr, self.fields))
        if attr in self.fields:
            if attr not in self._values:
                self.loadValues()
            val = self._values.get(attr)
            field = self.annotationschema.getField(attr)
            return field.deserialize(val)

        return super(CodedUnit, self).__getattribute__(attr)

    def loadValues(self):
        s = self.annotationschema
        vals = self.db.select(s.table, self._fields, self._getWhere())
        if len(vals) <> 1:
            raise ValueError("CodedUnit values %r not len==1 %s %s %s" % (vals, s.table, self._fields, self._getWhere()))
        self._values = dict(zip(self.fields, vals[0]))
        log.debug("Loaded %r" % self._values)
    
    @property
    def fields(self):
        if self._fields is None:
            self._fields = [f.fieldname for f in self.annotationschema.fields]
        return self._fields
    
    def getValue(self, field):
        if isinstance(field, annotationschema.AnnotationSchemaField):
            field = field.fieldname
        return getattr(self, field)

class CodedArticle(Cachable, CodedUnit):
    __table__ = 'codingjobs_articles'
    __idcolumn__ = 'codingjob_articleid'

    def __init__(self, *args, **kargs):
        Cachable.__init__(self, *args, **kargs)
        CodedUnit.__init__(self)
    
    article = DBProperty(lambda:article.Article)
    set = DBProperty(CodingJobSet)

    def getSentenceTable(self):
        return self.set.job.unitSchema.table
    def createSentence(self, db, arrowid):
        return CodedSentence(db, arrowid, self)
    sentences = ForeignKey(lambda:CodedSentence, constructor=createSentence)
    sentences.tablehook=getSentenceTable
#        self.addDBroperty("confidence", table=job.articleSchema.table, func = lambda c : c and (float(c) / 1000))

    @property
    def annotationschema(self):
        return self.set.job.articleSchema
    def getArticle(self):
        return self.article

    @property
    def confidence(self):
        return .99
    #confidence = DBProperty()self.addDBProperty("confidence", table=job.articleSchema.table, func = lambda c : c and (float(c) / 1000))

class CodedSentence(CodedUnit, Cachable):
    __idcolumn__ = 'arrowid'
    ca = DBProperty(CodedArticle)
    sentence = DBProperty(lambda:sentence.Sentence)
    
    
    def __init__(self, db, arrowid, ca):
        Cachable.__init__(self, db, arrowid)
        CodedUnit.__init__(self)
        self.ca = ca
        self.annotationschema = ca.set.job.unitSchema
        self.__table__ = self.annotationschema.table

# def getCodedArticle(db, cjaid):
#     cjid = db.getValue("select codingjobid from codingjobs_articles where codingjob_articleid = %i"  % cjaid)
#     job = getCodingJob(db, cjid)
#     return job.findCodedArticle(cjaid = cjaid)



def getCAJobs(cas):
    return sorted(set([ca.set.job for ca in cas]))
def getCACoders(cas):
    return sorted(set(ca.set.coder for ca in cas))


def getValue(row, schemafield):
    val = row.getValue(schemafield)
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
    print cj, cj.project
