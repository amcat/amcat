import dbtoolkit, alpino, dot


def sentences(db, sentenceids):
    for sentenceid in sentenceids:
        yield Sentence(db, sentenceid)


class Sentence(object):
    
    def __init__(self, db, id):
        self.db = db
        self.id = id
        self._fields = False
        
    def _getFields(self):
        if self._fields: return
        SQL = """
            SELECT articleid, parnr, sentnr, sentence, longsentence, encoding
            FROM sentences
            WHERE sentenceid = %i
        """ % self.id
        data = self.db.doQuery(SQL)
        if not data: raise Exception('sentence %d not found' % self.id)
        articleid, parnr, sentnr, text, longsentence, encoding = data[0]
        
        self.setFields(articleid, parnr, sentnr, text, longsentence, encoding)
        
        #self._article = self.db.article(articleid)
        
        
    def setFields(self, articleid, parnr, sentnr, text, longsentence, encoding):
        self._articleid = articleid
        self._parnr = parnr
        self._sentnr = sentnr
        if longsentence: text = longsentence
        text = dbtoolkit.decode(text, encoding)
        self._text = text
        self._fields = True
        
    @property
    def article(self):
        self._getFields()
        return self.db.article(self._articleid)
          
    @property
    def articleid(self):
        self._getFields()
        return self._articleid
        
      
    @property
    def sentnr(self):
        self._getFields()
        return self._sentnr
        
    @property
    def text(self):
        self._getFields()
        return self._text
        
    @property
    def parnr(self):
        self._getFields()
        return self._parnr
        
    @property
    def parsePicture(self):
        parse = alpino.fromdb(self.db, self.id)
        obj = dot.dot2object(parse.dot())
        return obj
    
    def getPreviousSentences(self, count=2):
        sql = """
            SELECT TOP %d sentenceid
            FROM sentences
            WHERE articleid = %d AND (parnr < %d OR (parnr = %d and sentnr < %d))
            ORDER BY parnr DESC, sentnr DESC
            """ % (count, self.articleid, self.parnr, self.parnr, self.sentnr)
        data = self.db.doQuery(sql)
        ids = [row[0] for row in data]
        ids.reverse()
        return sentences(self.db, ids)
        
    def getNextSentences(self, count=2):
        sql = """
            SELECT TOP %d sentenceid
            FROM sentences
            WHERE articleid = %d AND (parnr > %d OR (parnr = %d and sentnr > %d))
            ORDER BY parnr ASC, sentnr ASC
            """ % (count, self.articleid, self.parnr, self.parnr, self.sentnr)
        data = self.db.doQuery(sql)
        ids = [row[0] for row in data]
        return sentences(self.db, ids)