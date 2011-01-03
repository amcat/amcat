from amcat.tools.cachable.cachable import Cachable, ForeignKey, DBProperty
from amcat.tools import toolkit
from amcat.db import dbtoolkit
import re

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
    sentimentLemmata = ForeignKey(lambda:SentimentLemma)

    def sentimentLemma(self, lexicon):
        if type(lexicon) <> int: lexicon = lexicon.id
        for sl in self.sentimentLemmata:
            if sl.lexicon.id == lexicon:
                return sl
    
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



class SentimentLexicon(Cachable):
    __table__ = 'sentimentlexicons'
    __idcolumn__ = 'lexiconid'

    lemmata = ForeignKey(lambda:SentimentLemma)

    def lemmaidDict(self, cache=False):
        return dict((sl.lemmaid, sl) for sl in self.lemmata)

        
    
    
class SentimentLemma(Cachable):
    __table__ = 'words_lemmata_sentiment'
    __idcolumn__ = ('lexiconid', 'lemmaid')

    notes = DBProperty()
    sentiment = DBProperty(constructor = lambda o, db, sent : sent / 100.)
    intensity = DBProperty(constructor = lambda o, db, intensity : intensity / 100.)
    
    @property
    def lexicon(self):
        return SentimentLexicon(self.db, self.id[0])
    
    @property
    def lemmaid(self): return self.id[1]
                     
                     
    @property
    def lemma(self):
        return Lemma(self.db, self.lemmaid)
