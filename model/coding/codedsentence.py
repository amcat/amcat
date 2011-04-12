from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey
from amcat.tools.cachable.latebind import LB
from amcat.tools.cachable.codedvaluesproperty import CodedValuesProperty
from amcat.model.coding import codedvalues

class CodedSentence(Cachable, codedvalues.CodedValues):
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

    def delete(self, db):
        # Delete values, then delete self and invalidate parent
        ca = self.ca
        table = self.annotationschema.table
        idcol = "codingjob_articleid" if self.annotationschema.isarticleschema else "codedsentenceid"
        if table.lower() == "vw_net_arrows": table = "net_arrows" #HACK, remove after migrating to amcat3
        if table == "net_arrows": idcol = "arrowid" #HACK, remove after migrating!
                
        db.delete(table, {idcol: self.id})
        super(CodedSentence, self).delete(db)
        del ca.sentences
        del self.codedarticle
