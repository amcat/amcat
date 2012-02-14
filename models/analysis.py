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

from amcat.tools.model import AmcatModel
from amcat.models.language import Language
from amcat.models.word import Word

from django.db import models

class Analysis(AmcatModel):
    """Object representing an NLP 'preprocessing' analysis"""
    id = models.AutoField(db_column='analysis_id', primary_key=True)

    label = models.CharField(max_length=100)
    language = models.ForeignKey(Language)

    class Meta():
        db_table = 'parses_analyses'
        app_label = 'amcat'

class Relation(AmcatModel):
    id = models.IntegerField(db_column='relation_id', primary_key=True)
    label = models.CharField(max_length=100)
    
    class Meta():
        db_table = 'parses_relations'
        app_label = 'amcat'
        
class Pos(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='pos_id')
    major = models.CharField(max_length=100)
    minor = models.CharField(max_length=500)
    pos =  models.CharField(max_length=1, null=True)
        
    class Meta():
        db_table = 'parses_pos'
        app_label = 'amcat'

class Token(AmcatModel):
    __label__ = 'word'

    id = models.AutoField(primary_key=True, db_column='token_id')

    sentence = models.ForeignKey("amcat.Sentence", related_name="tokens")
    word = models.ForeignKey(Word)
    position = models.IntegerField()
    analysis = models.ForeignKey(Analysis)
    
    class Meta():
        db_table = 'parses_tokens'
        app_label = 'amcat'
        unique_together = ("sentence", "analysis", "position")
        ordering = ['sentence', 'position']
        
    def __unicode__(self):
        return unicode(self.word)


class Triple(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='triple_id')

    parent = models.ForeignKey(Token, related_name="+")
    child = models.ForeignKey(Token, related_name="+")
    relation = models.ForeignKey(Relation)
    analysis = models.ForeignKey(Analysis)
    
    class Meta():
        db_table = 'parses_triples'
        app_label = 'amcat'
        unique_together = ("analysis", "parent")



###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestTriples(amcattest.PolicyTestCase):
    def test_get_tokens_order(self):
        
        s = amcattest.create_test_sentence()
        w1, w2, w3 = [amcattest.create_test_word(word=x) for x in "abc"]
        a = Analysis.objects.create(label="X", language=w1.lemma.language)
        print a
        t1 = Token.objects.create(sentence=s, position=3, word=w3, analysis=a)
        t2 = Token.objects.create(sentence=s, position=1, word=w2, analysis=a)
        t3 = Token.objects.create(sentence=s, position=2, word=w1, analysis=a)

                
        self.assertEqual(list(s.tokens.all()), [t2,t3,t1])

        
