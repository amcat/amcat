from amcat.tools import toolkit
from amcat.tools.model import AmcatModel

from amcat.model.coding.annotationschema import AnnotationSchema
from amcat.model.user import User
from amcat.model.project import Project

from django.db import models

import logging; log = logging.getLogger(__name__)

def cacheCodingJobs(codingjobs, values=False, sentences=True, articles=True, schema=True):
    # TODO make caching smarter so this can be dumber
    if schema:
        cacher.cache(codingjobs, unitSchema=[], articleSchema=[])
        schemas = set(toolkit.flatten((job.unitSchema, job.articleSchema) for job in codingjobs))
        cacher.cache(schemas, "location", "isarticleschema", fields=["fieldname", "fieldtype","codebook","keycolumn","labelcolumn", "table"])
    if articles:
        article = {}
        if sentences:
            if values:
                article['sentences'] = ["values"]
            else:
                article['sentences'] = []
        if values:
            article['values'] = []
        cacher.cache(codingjobs, sets=dict(articles=article))

def getCodedArticlesFromCodingjobs(codingjobs, cache=True, cacheSentences=False, cacheValues=True):
    if cache: cacheCodingJobs(codingjobs, sentences=cacheSentences, values=cacheValues)
    for cj in codingjobs:
        for s in cj.sets:
            for ca in s.articles:
                yield ca
                    
def getCodedSentencesFromCodingjobs(codingjobs, cache=True, cacheValues=True):
    if cache: cacheCodingJobs(codingjobs, values=cacheValues)
    for ca in getCodedArticlesFromCodingjobs(codingjobs):
        for cs in ca.sentences:
            yield cs
            
class CodingJob(AmcatModel):
    id = model.IntegerKey(primary_key=True, db_column='codingjob_id')

    name = models.CharField(max_length=100)

    unitschema = models.ForeignKey(AnnotationSchema)
    articleschema = models.ForeignKey(AnnotationSchema)

    insertdate = models.DateTimeField()
    insertuser = models.ForeignKey(User)

    project = models.ForeignKey(Project)

    #sets = ForeignKey(LB("CodingJobSet", sub="coding"), includeOwnID=True)

    def __unicode__(self):
        return self.name

    class Meta():
        db_table = 'codingjobs'

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



    
if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True)

    cj = CodingJob(db, 423)
    print cj, cj.project
