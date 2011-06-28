###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################
from django.db import models

class String(models.Model):
    id = models.IntegerField(primary_key=True, db_column='stringid')
    
    string = models.CharField(max_length=100)

    class Meta():
        db_table = 'words_strings'

    def __unicode__(self):
        return self.string

class Lemma(models.Model):
    id = models.IntegerField(primary_key=True, db_column='lemmaid')

    pos = models.CharField(max_length=1)
    lemma = models.ForeignKey(String, db_column='stringid')

    # Snap ik niet?
    #sentimentLemmata = ForeignKey(lambda:SentimentLemma)

    class Meta():
        db_table = 'words_lemmata'
        app_label = 'models'

    def __unicode__(self):
        return unicode(self.lemma)

    def sentimentLemma(self, lexicon):
        if type(lexicon) != int:
            lexicon = lexicon.id

        for sl in self.sentimentLemmata:
            if sl.lexicon.id == lexicon:
                return sl

class Word(models.Model):
    id = models.IntegerField(primary_key=True, db_column='wordid')

    freq = models.IntegerKey(null=True)
    word = models.ForeignKey(String)
    lemma = models.ForeignKey(Lemma)
    celex = models.BooleanField(default=False)

    def __unicode__(self):
        return unicode(self.word)

    class Meta():
        db_table = 'words_words'
        app_label = 'models'

class SentimentLexicon(models.Model):
    id = models.IntegerKey(db_column='lexiconid')

    lemmata = ForeignKey(lambda:SentimentLemma)

    class Meta():
        db_table = 'sentimentlexicons'
        app_label = 'models'

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
