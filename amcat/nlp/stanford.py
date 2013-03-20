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
Preprocess using the Stanford dependency parser 
See http://nlp.stanford.edu/software/lex-parser.shtml
"""

import logging, re
log = logging.getLogger(__name__)

from amcat.nlp.analysisscript import VUNLPParser

CMD = "Stanford-CoreNLP"

class StanfordParser(VUNLPParser):
    parse_command = CMD

    def store_parse(self, parse):
        for i, words, tokens, triples in interpret_parse(parse):
            print i, words, tokens, triples
        

POSMAP = {
   '$' :'.',
   '"' :'.',
    "'" :'.',
   '``' : '.',
   "''" : '.',
   '(' :'.',
   ')' :'.',
   '-LRB-' : '.',
   '-RRB-' : '.',
   ',' :'.',
   '--' :'.',
   '.' :'.',
   ':' :'.',
   'CC' :'C',
   'CD' :'Q',
   'DT' :'D',
   'EX' :'R',
   'FW' :'?',
   'IN' :'P',
   'JJ' :'A',
   'JJR' :'A',
   'JJS' :'A',
   'LS' :'Q',
   'MD' :'V',
   'NN' :'N',
   'NNP' :'N',
   'NNPS' :'N',
   'NNS' :'N',
   'PDT' :'D',
   'POS' :'O',
   'PRP' :'O',
   'PRP$' :'O',
   'RB' :'B',
   'RBR' :'B',
   'RBS' :'B',
   'RP' :'R',
   'SYM' :'.',
   'TO' :'R',
   'UH' :'I',
   'VB' :'V',
   'VBD' :'V',
   'VBG' :'V',
   'VBN' :'V',
   'VBP' :'V',
   'VBZ' :'V',
   'WDT' :'D',
   'WP' :'O',
   'WP$' :'O',
   'WRB' :'B',
    }

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestStanford(amcattest.PolicyTestCase):
    def todo_test_parse(self):
        a = Stanford(None)
        
        tokens, triples = a.process_sentences([(99, "He wants\n coffee.")])
	he, wants, coffee, punc = tokens
	self.assertEqual(wants.pos, 'V')
	self.assertEqual(wants.lemma, 'want')
	self.assertEqual(wants.word, 'wants')
        self.assertEqual(len(triples), 2)
        self.assertIn(TripleValues(99, 2, 1, "dobj"), triples)


    def todo_test_unicode(self):
        a = Stanford(None)
        tokens, triples = a.process_sentences([(1, u"I am \u548c\u725b and I like caf\xe9s")])
        self.assertEqual(len(tokens), 7)
        self.assertEqual(tokens[2].word, u"\u548c\u725b")
        
        
