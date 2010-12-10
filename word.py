from cachable import Cachable, CachingMeta, DBFKPropertyFactory, DBPropertyFactory
import toolkit, re, dbtoolkit

class String(Cachable):
    __metaclass__ = CachingMeta
    __table__ = "words_strings"
    __idcolumn__ = "stringid"
    __labelprop__ = "string"
    __dbproperties__ = ["string"]

    def __str__(self): return self.label

class Lemma(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'words_lemmata'
    __idcolumn__ = 'lemmaid'
    __labelprop__ = "lemma"
    __dbproperties__ = ["pos"]
    lemma = DBPropertyFactory("stringid", dbfunc=String)
    
    def __str__(self): return self.lemma.label

class Word(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'words_words'
    __idcolumn__ = 'wordid'
    __labelprop__ = "word"
    __dbproperties__ = ["freq", "celex"]
    word = DBPropertyFactory("stringid", dbfunc=String)
    lemma = DBPropertyFactory("lemmaid", dbfunc=Lemma)

    def __str__(self): return self.word.label
    
