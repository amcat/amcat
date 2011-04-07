from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey
from amcat.tools.cachable.latebind import LB

from amcat.model.coding import codingjob
import logging; log = logging.getLogger(__name__)


def getCodingJobsSetsFromUser(db, userid, limit=None):
    limitSQL = 'top %d' % limit if limit else ''
    SQL = """select %s codingjobid, setnr from codingjobs_sets
             where coder_userid = %d
             order by codingjobid desc""" % (limitSQL, userid)
    data = db.doQuery(SQL)
    log.debug(data)
    for row in data:
        yield CodingJobSet(db, row[0], row[1])


class CodingJobSet(Cachable):
    __table__ = 'codingjobs_sets'
    __idcolumn__ = ['codingjobid', 'setnr']
    
    coder = DBProperty(LB("User"), getcolumn="coder_userid")
    articles = ForeignKey(LB("CodedArticle", sub="coding"))

    @property
    def job(self):
        return codingjob.CodingJob(self.db, self.jobid)
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

    def getArticleFromAid(self, aid):
        for a in self.articles:
            if a.article.id == aid:
                return a
                
    def getArticles(self):
        #cacheMultiple(self.articles, "article")
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
        
