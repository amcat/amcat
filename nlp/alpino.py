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
Preprocess using Alpino
See http://www.let.rug.nl/vannoord/alp/Alpino/ 
"""
import os, subprocess
from os.path import exists

import logging; log = logging.getLogger(__name__)

from amcat.nlp.analysisscript import AnalysisScript, Token, Triple
from amcat.tools.toolkit import execute, wrapped, to_list

CMD = "ALPINO_HOME={alpino_home} {alpino_home}/bin/Alpino {alpino_options}"
TOKENIZE = "{alpino_home}/Tokenization/tok" 
ALPINO_HOME="/home/amcat/resources/Alpino"
ALPINO_OPTIONS = "end_hook=dependencies -parse"

class Alpino(AnalysisScript):
    def __init__(self, analysis, alpino_home=ALPINO_HOME, alpino_options=ALPINO_OPTIONS):
        super(Alpino, self).__init__(analysis, triples=True)
        if not exists(alpino_home): alpino_home = os.environ['ALPINO_HOME']
        self.alpino_home = alpino_home
        self.alpino_options = alpino_options

    def _parse(self, tokens):
        cmd = CMD.format(**self.__dict__)
        log.debug("Parsing %s" % tokens)
        out, err = execute(cmd, tokens)
        log.debug(out)
        # it seems that alpino reports errors by starting a line with an exclamation mark
        if "\n! " in err:
            raise Exception("Error on parsing %r: %s" % (tokens, err))
        return out.decode("utf-8")

    def _tokenize(self, input):
        cmd = TOKENIZE.format(**self.__dict__)        
        return execute(cmd, input, outonly=True)

    def _get_input(self, sentences):
        input = "\n".join("{0.id}|{0.sentence}".format(s) for s in sentences)
        if input[-1] != "\n": input += "\n"
        return input.encode("utf-8")

    @wrapped(set)
    def get_tokens(self, sentence, memo=None):
        if memo is None: memo = self.preprocess_sentences([sentence])
        for sid, parent, child, rel in memo:
            yield parent
            yield child

    def get_triples(self, sentence, memo=None):
        if memo is None: memo = self.preprocess_sentences([sentence])
        for sid, parent, child, rel in memo:
            yield Triple(sid, child.position, parent.position, rel) 
    
    @to_list
    def preprocess_sentences(self, sentences):
        input = self._get_input(sentences)
        tokens = self._tokenize(input)
        rawparse = self._parse(tokens)
        for line in rawparse.split("\n"):
            if not line.strip(): continue
            yield interpret_line(line)
            
POSMAP = {"pronoun" : 'O',
          "verb" : 'V',
          "noun" : 'N',
          "preposition" : 'P',
          "determiner" : "D",
          "comparative" : "C",
          "adverb" : "B",
          'adv' : 'B',
          "adjective" : "A",
          "complementizer" : "C",
          "punct" : ".",
          "conj" : "C",
          "tag" : "?",
          "particle": "R",
          "name" : "M",
          "part" : "R",
          "intensifier" : "B",
          "number" : "Q",
          "cat" : "Q",
          "n" : "Q",
          "reflexive":  'O',
          "conjunct" : 'C',
          "pp" : 'P',
          'anders' : '?',
          'etc' : '?',
          'enumeration': '?',
          'np': 'N',
          'p': 'P',
          'quant': 'Q',
          'sg' : '?',
          'zo' : '?',
          'max' : '?',
          'mogelijk' : '?',
          'sbar' : '?',
          '--' : '?',
          }

def interpret_token(sid, lemma, word, begin, end, dummypos, dummypos2, pos):
    if "(" in pos:
        major, minor = pos.split("(", 1)
        minor = minor[:-1]
    else:
        major, minor = pos, None
    if "_" in major:
        m2 = major.split("_")[-1]
    else:
        m2 = major
    cat = POSMAP.get(m2)
    if not cat:
        raise Exception("Unknown POS: %r (%s/%s/%s/%s)" % (m2, major, begin, word, pos))
    return Token(sid, int(begin), word, lemma, cat, major, minor)


def interpret_line(line):
    data = line.split("|")
    if len(data) != 16:
        raise ValueError("Cannot interpret line %r, has %i parts (needed 16)" % (line, len(data)))
    sid = int(data[-1])
    parent = interpret_token(sid, *data[:7])
    child = interpret_token(sid, *data[8:15])
    func, rel = data[7].split("/")
    return sid, parent, child, rel.strip()

        

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestAlpino(amcattest.PolicyTestCase):
    def test_tokenize(self):
        a = Alpino(None)
        
        s1 = amcattest.create_test_sentence(sentence="daarom, toch?")
        s2 = amcattest.create_test_sentence(sentence="pas d'r op, a.u.b.")
        input = a._get_input([s1, s2])
        self.assertEqual(input, "{s1.id}|daarom, toch?\n{s2.id}|pas d'r op, a.u.b.\n".format(**locals()))
        
        tokens = a._tokenize(input)
        self.assertEqual(tokens, "{s1.id}|daarom , toch ?\n{s2.id}|pas d'r op , a.u.b.\n".format(**locals()))
        

    def test_parse_function(self):
        tokens = u"1|in Syri\xeb".encode('utf-8')
        a = Alpino(None)
        out = a._parse(tokens)
        token1 = u"in|in|0|1|prep|prep|preposition(in,[])"
        token2 = u"Syri\xeb|Syri\xeb|1|2|name|name(LOC)|proper_name(both,LOC)"
        self.assertEqual(out, u"{token1}|hd/obj1|{token2}|1\n".format(**locals()))

    def test_errors(self):
        a = Alpino(None)
        tokens = "1|ik woon in Syri\00"
        self.assertRaises(Exception, a._parse, tokens)
        

    def test_interpret(self):

        sentno = -124356789
        token_str1 = u"huis_DIM|huisje|1|2|noun|noun|noun(het,count,sg)"
        token_str2 = u"het|het|0|1|det|det(nwh)|determiner(het,nwh,nmod,pro,nparg,wkpro)"

        token1 = Token(sentno, 1, "huisje", "huis_DIM", "N", "noun", "het,count,sg")
        token2 = Token(sentno, 0, "het", "het", "D" ,"determiner", "het,nwh,nmod,pro,nparg,wkpro")
        
        
        self.assertEqual(interpret_token(sentno, *token_str1.split("|")), token1)
        self.assertEqual(interpret_token(sentno, *token_str2.split("|")), token2)

        line = u"{token_str1}|hd/det|{token_str2}|{sentno}\n".format(**locals())

        sid, t1, t2, rel = interpret_line(line)

        self.assertEqual(sid, sentno)
        self.assertEqual(t1, token1)
        self.assertEqual(t2, token2)
        self.assertEqual(rel, "det")

    def test_parse(self):
        a = Alpino(None)
        s = amcattest.create_test_sentence(sentence="ik zie hem!")
        tokens, triples = a.process_sentence(s)
        self.assertEqual(len(tokens), 4)
        self.assertIn(Token(s.id, 3, "!", "!", ".", "punct", "uitroep"), tokens)
        
        self.assertEqual(set(triples), {
                Triple(s.id, 0, 1, "su"),
                Triple(s.id, 2, 1, "obj1"),
                Triple(s.id, 3, 1, "--"),})

if __name__ == '__main__':
    from amcat.tools import amcatlogging
    amcatlogging.setup()
    a = Alpino(None)
    print a._tokenize("-1|dit is een test\n")
    
