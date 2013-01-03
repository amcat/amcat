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

from amcat.models.token import TripleValues, TokenValues

import re
import logging
log = logging.getLogger(__name__)

from amcat.nlp.analysisscript import AnalysisScript, Parser, ParserError
from amcat.tools.toolkit import execute

CMD = ("java -cp {parser_home}/stanford-parser-2012-05-22-models.jar:{parser_home}/stanford-parser.jar "
       "-mx600m edu.stanford.nlp.parser.lexparser.LexicalizedParser "
       "-sentences newline -retainTMPSubcategories -outputFormat wordsAndTags,typedDependencies "
       "-outputFormatOptions stem,basicDependencies "
       "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz -")

def clean(sent):
    return re.sub("\s+", " ", sent).strip()
        
class Stanford(Parser):
    ENVIRON_HOME_KEY = "STANFORD_HOME"
    DEFAULT_HOME = "/home/amcat/resources/Stanford"

    def _parse(self, input):
        self._check_home()
        cmd = CMD.format(**self.__dict__)
        log.debug("Parsing %r" % input)
        out, err = execute(cmd, input.encode("utf-8"))
        if "*******" in err:
            raise ParserError("Exception from Stanford parser: %r" % err)
        log.debug("OUT: %r\nERR:%r\n" % (out, err))
        return out.decode("utf-8"), err.decode("utf-8")

    def get_tokens(self, id, sentence, memo=None):
        return memo[id][0]

    def get_triples(self, id, sentence, memo=None):
        return memo[id][1]

    def preprocess_sentences(self, sentences):
        input = "\n".join(clean(sent) for (sid, sent) in sentences)
        sids = [sid for (sid, sent) in sentences]
        out, err = self._parse(input)
        memo = dict(interpret_parse(sids, out, err))        
        return memo

def create_tokens(sid, words, tokens):
    for position, s in enumerate(tokens):
        lemma, pos = s.rsplit("/", 1)
        poscat = POSMAP[pos]
        
        yield TokenValues(sid, position, words[position], lemma, poscat, pos, None)

def create_triples(sid, triples):
    for parent, rel, child in triples:
        yield TripleValues(sid, child-1, parent-1, rel)
        
def interpret_parse(sids, out, err):
    words = dict(interpret_err(err))
    tokens_triples = dict(interpret_out(out))
    for i, sid in enumerate(sids):
        tokens, triples = tokens_triples[i]
        tokens = list(create_tokens(sid, words[i], tokens))
        triples = list(create_triples(sid, triples))
        yield sid, (tokens, triples)
    
def interpret_err(err):
    for line in err.split("\n"):
        m = re.match(r"Parsing \[sent. (\d+) len. \d+\]: (.*)", line.strip())
        if m:
            i, sent = m.groups()
            yield int(i)-1, sent.split(" ") # to get 0-based offset
            
def interpret_out(out):
    # output of correctly parsed sentences is of form
    # tokens / empty / triple / ... / triple / empty
    # output of error is of form
    # Sentence skipped: / SENTENCE_SKIPPED (no empty line)  <- does this actually happen anymore?
    lines = out.split("\n")
    i = -1 # start with index -1 + 1 = 0
    def expect(s):
        line = lines.pop(0)
        if line.strip() <> s: raise ParserError("Expected %r, got %r" % (s, line))
    while lines:
        tokens = lines.pop(0)
        if not tokens: continue # skip leading empty lines
        i += 1
        if tokens.startswith("Sentence skipped:"):
            expect("SENTENCE_SKIPPED_OR_UNPARSABLE")
            log.warn("Sentence #%i was skipped or unparsable" % i)
            log.debug("Lines now %r" % lines)
            continue
        tokens = tokens.split(" ")

        log.debug("Read tokens %r, reading triples..." % tokens)
        log.debug("Lines now %r" % lines)
        
        triples = []
        expect("")
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
        log.debug("Done! i=%i, tokens=%s, triples=%s" % (i, tokens, triples))
        yield i, (tokens, triples)
    

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
    def test_parse(self):
        a = Stanford(None)
        
        tokens, triples = a.process_sentences([(99, "He wants\n coffee.")])
	he, wants, coffee, punc = tokens
	self.assertEqual(wants.pos, 'V')
	self.assertEqual(wants.lemma, 'want')
	self.assertEqual(wants.word, 'wants')
        self.assertEqual(len(triples), 2)
        self.assertIn(TripleValues(99, 2, 1, "dobj"), triples)


    def test_unicode(self):
        a = Stanford(None)
        tokens, triples = a.process_sentences([(1, u"I am \u548c\u725b and I like caf\xe9s")])
        self.assertEqual(len(tokens), 7)
        self.assertEqual(tokens[2].word, u"\u548c\u725b")
        
        
