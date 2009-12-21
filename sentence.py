import dbtoolkit
from cachable import Cachable
from functools import partial
import article as articlemodule

class Sentence(Cachable):
    __table__ = 'sentences'
    __idcolumn__ = 'sentenceid'
    __labelprop__ = 'text'
    
    def __init__(self, db, id, article=None):
        Cachable.__init__(self, db, id)
        self.addDBProperty("article", "articleid", func=partial(articlemodule.Article, db))
        for prop in "parnr", "sentnr", "encoding":
            self.addDBProperty(prop)
        self.addDBProperty("text", "isnull(longsentence, sentence)", self.decode)
        if article is not None: self.cacheValues(article = article)
        
    def decode(self, s):
        return dbtoolkit.decode(s, self.encoding)
