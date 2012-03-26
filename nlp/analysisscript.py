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

Token = namedtuple("Token", ["sentence_id", "position", "word", "lemma", "pos", "major", "minor"])
Triple = namedtuple("Triple", ['Sentence_id', "child", "parent", "relation"])


class AnalysisScript(object):
    def __init__(self, analysis, tokens=True, triples=False):
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
