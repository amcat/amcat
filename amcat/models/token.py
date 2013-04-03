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
from amcat.models import Word
from django.db import models
from collections import namedtuple

TripleValues = namedtuple("TripleValues", ["analysis_sentence", "child", "parent", "relation"])
TokenValues = namedtuple("TokenValues", ["analysis_sentence", "position", "word", "lemma", "pos", "major", "minor", "namedentity"])

class Pos(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='pos_id')
    major = models.CharField(max_length=100)
    minor = models.CharField(max_length=500, null=True)
    pos =  models.CharField(max_length=1, null=True)

    class Meta():
        db_table = 'tokens_pos'
        app_label = 'amcat'

class Token(AmcatModel):
    __label__ = 'word'

    id = models.AutoField(primary_key=True, db_column='token_id')

    sentence = models.ForeignKey("amcat.AnalysisSentence", related_name="tokens")
    word = models.ForeignKey(Word)
    position = models.IntegerField()
    pos = models.ForeignKey(Pos, related_name="+")
    namedentity = models.CharField(max_length=1, null=True, blank=True)

    class Meta():
        db_table = 'tokens'
        app_label = 'amcat'
        unique_together = ("sentence", "position")
        ordering = ['sentence', 'position']
        
    def __unicode__(self):
        return unicode(self.word)

class Relation(AmcatModel):
    id = models.AutoField(db_column='relation_id', primary_key=True)
    label = models.CharField(max_length=100)

    class Meta():
        db_table = 'tokens_triples_relations'
        app_label = 'amcat'

class Triple(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='triple_id')

    parent = models.ForeignKey(Token, related_name="+")
    child = models.ForeignKey(Token, related_name="+")
    relation = models.ForeignKey(Relation)

    class Meta():
        db_table = 'tokens_triples'
        app_label = 'amcat'
        unique_together = ('parent', 'child', 'relation')


class CoreferenceSet(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='coreference_set_id')
    analysed_article = models.ForeignKey("amcat.AnalysedArticle", related_name='coreferencesets')
    tokens = models.ManyToManyField(Token, related_name='coreferencesets')

    class Meta():
        db_table = 'coreferencesets'
        app_label = 'amcat'

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestTokens(amcattest.PolicyTestCase):
    def test_get_tokens_order(self):
        s = amcattest.create_test_analysis_sentence()
        t1,t2,t3 = [amcattest.create_test_token(sentence=s, position=i) for i in [2,1,3]]

        self.assertEqual(list(s.tokens.all()), [t2,t1,t3])
