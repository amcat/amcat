from export_codingjobresults import ExportScript, FieldColumn
import table3
import codingjob,  ont
import cachable
import logging; log = logging.getLogger(__name__)

def getTable(jobs, *args, **kargs):
    return AgendaExportScript(*args, **kargs).getTable(jobs)

class TwoDigitFieldColumn(FieldColumn):
    """Returns two-digit code for an ontolgoy field
    (capic1, capic2, capic3)"""
    
    def __init__(self, field, article):
        FieldColumn.__init__(self, field, article)
        self.label = field.fieldname + (' (two-digit)')
            
    def getCell(self, row):
        ontf = super(TwoDigitFieldColumn, self).getCell(row)
        if not ontf: return None
        return str(ontf)[:2]
    
class FourDigitFieldColumn(FieldColumn):
    """Returns four-digit code for an ontolgoy field
    (capic1, capic2, capic3)"""
    
    def __init__(self, field, article):
        FieldColumn.__init__(self, field, article)
        self.label = field.fieldname + (' (four-digit)')
            
    def getCell(self, row):
        ontf = super(FourDigitFieldColumn, self).getCell(row)
        if not ontf: return None
        return str(ontf)[:4]
    
class LabelFieldColumn(FieldColumn):
    """Returns label for an ontolgoy field
    (capic1, capic2, capic3)"""
    
    def __init__(self, field, article):
        FieldColumn.__init__(self, field, article)
        self.label = field.fieldname + (' (label)')
            
    def getCell(self, row):
        ontf = super(LabelFieldColumn, self).getCell(row)
        if not ontf: return None
        lbl = ontf.labels.get(self.field.schema.language)
        if lbl is None: lbl = str(ontf)
        return lbl[4:]

class AgendaExportScript(ExportScript):
    """Filter build for """

    def __init__(self, *args, **kargs):
        ExportScript.__init__(self, *args, **kargs)
        self._Cache = None
    
    
    def getColumn(self, field, article):
       if issubclass(field.getTargetType(), ont.Object):
           #if str(field) in ['capic1', 'capic2', 'capic3']:
           yield TwoDigitFieldColumn(field, article)
           yield FourDigitFieldColumn(field, article)
           yield LabelFieldColumn(field, article)
       else:
           yield FieldColumn(field, article)
    
    def getColumns(self, jobs):
        self.cacheFroms(jobs)
        
        return (self.getMetaColumns()
                + [table3.ObjectColumn("Confidence", self.confidence)]
                + [table3.ObjectColumn("Quasi", self.quasiSentence)]
                + list(self.getArticleAnnotationColumns(jobs))
                + list(self.getUnitAnnotationColumns(jobs))
                )
        
    def cacheFroms(self, jobs):
        """As explained below in quasiSentence(), a row has to be compared
        to all other codings of the same sentence.
        
        This caches all the sentence id's and their 'froms'."""
        self._Cache = {}
        for r in self.getRows(jobs):
            if not r.cs:
                continue
            
            try:
                self._Cache[r.cs.sentence.id]
            except KeyError:
                self._Cache[r.cs.sentence.id] = []
            
            self._Cache[r.cs.sentence.id].append(r.cs.getValue("from"))
            
    def getCodedArticles(self, jobs):
        cachable.cache(jobs, sets=dict(articles=[]))#"confidence"]))
        return codingjob.getCodedArticlesFromCodingjobs(jobs)
            
    def confidence(self, row):
        try:
            
            row.ca.fields # force cache
            row.ca._fields["confidence"] = lambda x:x/1000. # add confidence pseudo-field
            return row.ca.confidence
        except Exception, e:
            log.error(e)
            return None
            
    def quasiSentence(self, row):
        """Split a sentence according to the 'from'-field.
        
        Some sentences may be coded more than one time where each 'coding'
        applies to a part of the sentence.
        
        For example, the sentence 'Python is an impeccable language' may
        be encoded 3 times. If we assume the first coding has a from-field
        of NULL, the second has 3 and the last one has 4, then these are
        the parts belonging to each 'coding':
        
        #, part
        1, Python is an
        2, impeccable
        3, language  
        """
        if not row.cs:
            return
        
        #if self._Cache == None:
        #    self.cacheFroms([row.ca.set.job])
        
        # Get 'from' value
        fr = row.cs.getValue("from")
        
        # Compare current row to the other rows (of the same sentence)
        to = None
        for i in self._Cache[row.cs.sentence.id]:
            if (fr < i):
               to = i
        
        # Split sentence into words
        words = row.cs.sentence.text.split()
        
        # Glue the words back together again
        return ' '.join(words[fr:to])

if __name__ == '__main__':
    AgendaExportScript().runFromCommand()
    
