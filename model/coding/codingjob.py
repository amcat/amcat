from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.tools.cachable.latebind import LB

import logging; log = logging.getLogger(__name__)

def getCodedArticlesFromCodingjobs(codingjobs):
    for cj in codingjobs:
        for s in cj.sets:
            for ca in s.articles:
                yield ca
                    
def getCodedSentencesFromCodingjobs(codingjobs):
    cache(codingjobs, sets=dict(articles=dict(article=["sentences"], sentences=[])))
    for ca in getCodedArticlesFromCodingjobs(codingjobs):
        for cs in ca.sentences:
            yield cs
            
class CodingJob(Cachable):
    __table__ = 'codingjobs'
    __idcolumn__ = 'codingjobid'
    __labelprop__ = 'name'
    name, insertdate = DBProperties(2)

    unitSchema = DBProperty(LB("AnnotationSchema", package="amcat.model.coding"), getcolumn="unitschemaid")
    articleSchema = DBProperty(LB("AnnotationSchema", package="amcat.model.coding"), getcolumn="articleschemaid")
    project = DBProperty(LB("Project"))
    owner = DBProperty(LB("User"), getcolumn="owner_userid")

    sets = ForeignKey(LB("CodingJobSet", sub="coding"), includeOwnID=True)
        
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
