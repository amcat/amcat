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

from itertools import chain
import os
from os.path import exists

class AnalysisScript(object):
    def __init__(self, analysis, tokens=False, triples=False):
        self.analysis = analysis
        self.tokens = tokens
        self.triples = triples

    def preprocess_sentences(self, sentences):
        """
        Optional preprocessing of the sentence. The result (which can be an
        arbitrary object) is passed to the get_triples and get_tokens methods.
        @param sentences: a sequence of id : sentence pairs
        """

    def get_triples(self, id, sentence, memo=None):
        """
        @param id: the (analysis_sentence) id of the sentence
        @param sentence: the sentence string
        @return: a sequence of TripleValues objects
        """
        raise NotImplementedError()

    def get_tokens(self, id, sentence, memo=None):
        """
        @param id: the (analysis_sentence) id of the sentence
        @param sentence: the sentence string
        @return: a sequence of TokenValues objects
        """
        raise NotImplementedError()

    def process_sentences(self, sentences):
        """
        Process the given sentences with this script
        @param sentences:  a sequence of id : sentence pairs
        @return: a sequence of TokenValues objects
        """
        sentences = list(sentences)
        memo = self.preprocess_sentences(sentences)
        tokens = list(chain.from_iterable(self.get_tokens(id, s, memo) for (id, s) in sentences)
                  if  self.tokens else None)
        triples = list(chain.from_iterable(self.get_triples(id, s, memo) for (id, s) in sentences)
                   if  self.triples else None)
        return tokens, triples


    def run(self, _input=None):
        raise NotImplementedError


class ParserConfigurationError(Exception): pass
class ParserError(EnvironmentError): pass

class Parser(AnalysisScript):
    """Analysisscript subclass for parsers bound to a specific ('home') folder"""
    
    ENVIRON_HOME_KEY = None
    DEFAULT_HOME = None
    
    def __init__(self, analysis, parser_home=None):
        super(Parser, self).__init__(analysis, triples=True, tokens=True)
        if parser_home is not None:
            self.parser_home = parser_home
        else:
            try:
               self.parser_home = os.environ[self.ENVIRON_HOME_KEY]
            except KeyError:
                self.parser_home = self.DEFAULT_HOME

    def _check_home(self):
        if self.parser_home is None:
            raise ParserConfigurationError("{} not specified".format(self.ENVIRON_HOME_KEY))
        if not exists(self.parser_home):
            raise ParserConfigurationError("Cannot find {self.ENVIRON_HOME_KEY}: {self.parser_home}"
                                           .format(**locals()))

    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAnalysisScript(amcattest.PolicyTestCase):
    def test_process(self):
        from amcat.models.token import TokenValues
        class X(AnalysisScript):
            def __init__(self):
                super(X, self).__init__(analysis=None, tokens=True, triples=False)

            def get_tokens(self, analysis_sentence, memo=None):
                for i, x in enumerate(analysis_sentence.sentence.sentence.split()):
                    yield TokenValues(analysis_sentence, i+1, x, None, None, None, None)
        a = amcattest.create_test_analysis_sentence(sentence=amcattest.create_test_sentence(sentence="dit is een test"))
        tokens, triples = list(X().process_sentence(a))
        print(tokens)
        self.assertIsNone(triples)
        self.assertEqual(list(tokens)[0], (TokenValues(a, 1, "dit", None, None, None, None)))
