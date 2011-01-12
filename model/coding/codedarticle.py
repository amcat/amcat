from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey
from amcat.tools.cachable.codedvaluesproperty import CodedValuesProperty
from amcat.tools.cachable.latebind import LB
from amcat.model.coding import codedsentence


class CodedArticle(Cachable):
    __table__ = 'codingjobs_articles'
    __idcolumn__ = 'codingjob_articleid'
    #sentences = ForeignKey(LB("CodedSentence", sub="coding"), constructor=createSentence)
    
    article = DBProperty(LB("Article"))
    set = DBProperty(LB("CodingJobSet", sub="coding"))
    values = CodedValuesProperty(lambda ca: ca.annotationschema)
    sentences = ForeignKey(LB("CodedSentence", sub="coding"))
    
    def getSentenceTable(self):
        return self.set.job.unitSchema.table
    def createSentence(self, db, arrowid):
        return codedsentence.CodedSentence(db, arrowid, self)

    @property
    def annotationschema(self):
	return self.set.job.articleSchema
    
    def getArticle(self):
        return self.article

    #confidence = DBProperty()self.addDBProperty("confidence", table=job.articleSchema.table, func = lambda c : c and (float(c) / 1000))

