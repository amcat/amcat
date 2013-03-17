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

CMD = ("Stanford edu.stanford.nlp.parser.lexparser.LexicalizedParser "
       "-sentences newline "
       "-retainTMPSubcategories "
       "-outputFormat words,wordsAndTags,typedDependencies "
       "-outputFormatOptions stem,basicDependencies "
       "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz")

class StanfordParser(VUNLPParser):
    parse_command = CMD

    def store_parse(self, parse):
        for i, words, tokens, triples in interpret_parse(parse):
            print i, words, tokens, triples
        

def interpret_parse(out):
    # output of correctly parsed sentences is of form
    # words / empty / tokens / empty / triple / ... / triple / empty
    # output of error is of form
    # Sentence skipped: / SENTENCE_SKIPPED (no empty line)  <- does this actually happen anymore?
    lines = out.split("\n")
    i = -1 # start with index -1 + 1 = 0
    def expect(s):
        line = lines.pop(0)
        if line.strip() <> s: raise ParserError("Expected %r, got %r" % (s, line))
    while lines:
        line = lines.pop(0)
        if not line: continue # skip leading empty lines
        i += 1
        if line.startswith("Sentence skipped:"):
            expect("SENTENCE_SKIPPED_OR_UNPARSABLE")
            log.warn("Sentence #%i was skipped or unparsable" % i)
            log.debug("Lines now %r" % lines)
            continue

        words = line.split()
        expect("")
        
        tokens = lines.pop(0).split(" ")
        expect("")
        
        log.debug("Read words %r, tokens %r, reading triples..." % (words, tokens))
        log.debug("Lines now %r" % lines)

        triples = []
        while True:
            triple = lines.pop(0)
            log.debug("Read triple %r..." % triple)
            log.debug("Lines now %r" % lines)
            if not triple: break
            m = re.match(r"([\w&]+)\(.+-(\d+), .+-(\d+)\)", triple)
            if not m: raise Exception("Cannot interpret triple %s" % triple)
            rel, p1, p2 = m.groups()
            triple = (int(p1), rel, int(p2))
            if not (rel == 'root' and int(p1) == 0):
                triples.append(triple)
        log.debug("Done! i=%i, words=%r, tokens=%r, triples=%r" % (i, words, tokens, triples))
        yield i, words, tokens, triples
    

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
        
        
