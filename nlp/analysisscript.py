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

"""
Abstract analysis scripts for preprocessing
"""
from collections import namedtuple

from django.db import transaction
from amcat.models import ArticleAnalysis

from amcat.scripts.script import Script
from amcat.nlp.sbd import SBD

Token = namedtuple("Token", ["sentence_id", "position", "word", "lemma", "pos", "major", "minor"])
Triple = namedtuple("Triple", ['sentence_id', "child", "parent", "relation"])

class AnalysisScript(Script):
    def __init__(self, analysis, tokens=False, triples=False):
        self.analysis = analysis
        self.tokens = tokens
        self.triples = triples

    def preprocess_sentence(self, sentence):
        """
        Optional preprocessing of the sentence. The result (which can be an
        arbitrary object) is passed to the get_triples and get_tokens methods.
        """

    def get_triples(self, sentence, memo=None):
        """
        @return: a sequence of amcat.nlp.analysisscript.Triple objects
        """
        raise NotImplementedError()

    def get_tokens(self, sentence, memo=None):
        """
        @return: a sequence of amcat.nlp.analysisscript.Token objects
        """
        raise NotImplementedError()

    def process_sentence(self, sentence):
        memo = self.preprocess_sentence(sentence)
        tokens = self.get_tokens(sentence, memo) if self.tokens else None
        triples = self.get_triples(sentence, memo) if self.triples else None
        return tokens, triples

    @property
    def needs_preparation(self):
        return (self.tokens or self.triples)
    
    @transaction.commit_on_success
    def prepare_articles(self, article_analyses):
        if not self.needs_preparation: return
        sbd = SBD()
        for aa in article_analyses:
            if aa.article.sentences.count() > 1: continue
            for sentence in sbd.get_sentences(aa.article):
                sentence.save()
        ArticleAnalysis.objects.filter(pk__in=article_analyses).update(prepared=True)

    def run(self, _input=None):
        raise NotImplementedError

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAnalysisScript(amcattest.PolicyTestCase):
    def test_process(self):
        class X(AnalysisScript):
            def get_tokens(self, sentence, memo=None):
                for i, x in enumerate(sentence.sentence.split()):
                    yield Token(sentence.id, i+1, x, None, None, None, None)
        s = amcattest.create_test_sentence(sentence="dit is een test")
        tokens, triples = list(X(analysis=None).process_sentence(s))
        self.assertEqual(list(tokens)[0], (Token(s.id, 1, "dit", None, None, None, None)))
