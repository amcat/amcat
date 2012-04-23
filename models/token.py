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
from amcat.tools.djangotoolkit import get_or_create
from amcat.models import Word, Sentence
from django.db import models
from collections import namedtuple

TripleValues = namedtuple("TripleValues", ["analysis_sentence", "child", "parent", "relation"])

class TokenValues(namedtuple("TokenValues", ["analysis_sentence", "position", "word", "lemma", "pos", "major", "minor"])):
    def create(self):
        from amcat.models.analysis import AnalysisSentence
        s = (AnalysisSentence.objects.get(pk=self.analysis_sentence) if isinstance(self.analysis_sentence, int)
             else self.analysis_sentence)
        w = Word.get_or_create(s.analysis_article.analysis.language, self.lemma, self.pos, self.word)
        p = get_or_create(Pos, major=self.major, minor=self.minor, pos=self.pos)
        return Token.objects.create(sentence=s, position=self.position, word=w, pos=p)


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
        unique_together = ('parent', 'child')


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestTokens(amcattest.PolicyTestCase):
    def test_get_tokens_order(self):

        s = amcattest.create_test_sentence()
        w1, w2, w3 = [amcattest.create_test_word(word=x) for x in "abc"]
        a = Analysis.objects.create(language=w1.lemma.language)
        pos = Pos.objects.create(major="x", minor="y", pos="p")
        t1 = Token.objects.create(sentence=s, position=3, word=w3, analysis=a, pos=pos)
        t2 = Token.objects.create(sentence=s, position=1, word=w2, analysis=a, pos=pos)
        t3 = Token.objects.create(sentence=s, position=2, word=w1, analysis=a, pos=pos)

        self.assertEqual(list(s.tokens.all()), [t2,t3,t1])

    def test_get_analysis(self):
        from amcat.nlp.frog import Frog
        l = Language.objects.create()
        p = Plugin.objects.create(label='test', module='amcat.nlp.frog', class_name='Frog')
        a = Analysis.objects.create(language=l, plugin=p)
        self.assertEqual(a.plugin.get_class(), Frog)
        f =a.get_script()
        self.assertEqual(type(f), Frog)
        self.assertFalse(f.triples)

    def test_create_token(self):
        a = amcattest.create_test_analysis()
        token = amcattest.create_analysis_token()
        t = Token.create(a, token)
        self.assertEqual(t.sentence.id, token.sentence_id)
        self.assertEqual(t.word.word, token.word)
        self.assertEqual(t.word.lemma.pos, token.pos)
