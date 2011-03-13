from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey
from amcat.tools.cachable.latebind import LB
from amcat.tools.cachable.codedvaluesproperty import CodedValuesProperty

class CodedSentence(Cachable):
    __idcolumn__ = 'codedsentenceid'
    __table__ = 'codedsentences' 
    codedarticle = DBProperty(LB("CodedArticle", sub="coding"))
    sentence = DBProperty(LB("Sentence"))
    values = CodedValuesProperty(lambda cs: cs.annotationschema)
    

    @property
    def ca(self):
        return self.codedarticle
    @property
    def annotationschema(self):
        return self.ca.set.job.unitSchema
