from cachable2 import Cachable, ForeignKey, DBProperty
import toolkit, re, dbtoolkit

class String(Cachable):
    __table__ = "words_strings"
    __idcolumn__ = "stringid"
    __labelprop__ = "string"
    string = DBProperty()

class Lemma(Cachable):
    __table__ = 'words_lemmata'
    __idcolumn__ = 'lemmaid'
    __labelprop__ = "lemma"
    __dbproperties__ = ["pos"]
    pos = DBProperty()
    lemma = DBProperty(String)
    @property
    def label(self): return self.lemma.label

class Word(Cachable):
    __table__ = 'words_words'
    __idcolumn__ = 'wordid'
    __labelprop__ = "word"
    freq = DBProperty()
    celex = DBProperty()
    word = DBProperty(String)
    lemma = DBProperty(Lemma)
    @property
    def label(self): return self.word.label
