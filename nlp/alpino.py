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
#TODO: should use Parser superclass and remove HOME code

import os
from os.path import exists

#from amcat.models.token import TripleValues, TokenValues
from collections import namedtuple
TripleValues = namedtuple("TripleValues", ["analysis_sentence", "child", "parent", "relation"])
TokenValues = namedtuple("TokenValues", ["analysis_sentence", "position", "word", "lemma", "pos", "major", "minor", "namedentity"])

import logging
from amcat.tools import toolkit

log = logging.getLogger(__name__)

from amcat.nlp.analysisscript import AnalysisScript
from amcat.tools.toolkit import execute, wrapped

CMD = "ALPINO_HOME={alpino_home} {alpino_home}/bin/Alpino {alpino_options}"
TOKENIZE = "{alpino_home}/Tokenization/tok"
ALPINO_HOME="/home/amcat/resources/Alpino"
ALPINO_OPTIONS = "end_hook=dependencies -parse"
class AlpinoConfigurationError(Exception): pass
class AlpinoError(EnvironmentError): pass


class Alpino(AnalysisScript):
    def __init__(self, analysis, alpino_home=ALPINO_HOME, alpino_options=ALPINO_OPTIONS):
        super(Alpino, self).__init__(analysis, triples=True, tokens=True)
        if not exists(alpino_home): alpino_home = os.environ.get('ALPINO_HOME')
        self.alpino_home = alpino_home
        self.alpino_options = alpino_options

    def _parse(self, tokens):
        self._check_alpino()
        cmd = CMD.format(**self.__dict__)
        log.debug("Parsing %s" % tokens)
        out, err = execute(cmd, tokens.encode("latin-1"))
        log.debug(out)
        # it seems that alpino reports errors by starting a line with an exclamation mark
        if "\n! " in err:
            raise AlpinoError("Error on parsing %r: %s" % (tokens, err))
        return out.decode("latin-1")

    def _check_alpino(self):
        if self.alpino_home is None: raise AlpinoConfigurationError("ALPINO_HOME not specified")
        if not exists(self.alpino_home):
            raise AlpinoConfigurationError("Cannot find {self.alpino_home".format(**locals()))

    def _sanitize(self, input):
        input = toolkit.stripAccents(input, latin1=True)
        input = input.replace("\n", " ")# alpino will stop parsing on line break
        input = input.replace("|", "-") # | is field separator and we don't care anyway
        input = input.encode('latin-1', 'ignore').decode('latin-1')
        return input

    def _tokenize(self, input):
        self._check_alpino()
        cmd = TOKENIZE.format(**self.__dict__)
        return execute(cmd, input.encode("utf-8"), outonly=True).decode("utf-8")

    def _get_input(self, analysis_sentences):
        input = u"\n".join(u"{0}|{1}".format(id, self._sanitize(sent))
                           for (id, sent) in analysis_sentences)
        if input[-1] != "\n": input += "\n"
        return input

    @wrapped(set)
    def get_tokens(self, id, sentence, memo=None):
        for parent, child, rel in memo.get(id, []):
            yield parent
            yield child

    def get_triples(self, id, sentence, memo=None):
        for parent, child, rel in memo.get(id, []):
            yield TripleValues(id, child.position, parent.position, rel)

    def preprocess_sentences(self, sentences):
        memo = {} # sid : [(parent, child, rel), ...]
        input = self._get_input(sentences)
        tokens = self._tokenize(input)
        rawparse = self._parse(tokens)
        for line in rawparse.split("\n"):
            if not line.strip(): continue
            sid, parent, child, rel = interpret_line(line)
            memo.setdefault(sid, []).append((parent, child, rel))
        return memo

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

def interpret_token(sid, lemma, word, begin, _end, dummypos, dummypos2, pos):
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
    return TokenValues(sid, int(begin), word, lemma, cat, major, minor, None)


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

        input = a._get_input(enumerate(["daarom, toch?", "pas d'r op, a.u.b."]))
        self.assertEqual(input, "0|daarom, toch?\n1|pas d'r op, a.u.b.\n".format(**locals()))

        tokens = a._tokenize(input)
        self.assertEqual(tokens, "0|daarom , toch ?\n1|pas d'r op , a.u.b.\n".format(**locals()))


    def test_parse_function(self):
        tokens = u"1|een dezer Syri\xebrs"
        a = Alpino(None)
        out = a._parse(tokens)

        syriers = u"Syri\xebr|Syri\xebrs|2|3|noun|noun|noun(de,count,pl)"
        dezer = "deze|dezer|1|2|det|det|determiner(der)"
        een = u"\xe9\xe9n|een|0|1|pron|pron(strpro,nwh)|pronoun(nwh,thi,sg,both,both,indef,strpro)"
        expected = u"{syriers}|hd/det|{dezer}|1\n{een}|hd/mod|{syriers}|1\n".format(**locals())
        self.assertEqual(out, expected)

    def test_errors(self):
        a = Alpino(None)
        tokens = "1|ik woon in Syri\00"
        self.assertRaises(AlpinoError, a._parse, tokens)


    def test_interpret(self):

        sentno = -124356789
        token_str1 = u"huis_DIM|huisje|1|2|noun|noun|noun(het,count,sg)"
        token_str2 = u"het|het|0|1|det|det(nwh)|determiner(het,nwh,nmod,pro,nparg,wkpro)"

        token1 = TokenValues(sentno, 1, "huisje", "huis_DIM", "N", "noun", "het,count,sg", None)
        token2 = TokenValues(sentno, 0, "het", "het", "D" ,"determiner", "het,nwh,nmod,pro,nparg,wkpro", None)


        self.assertEqual(interpret_token(sentno, *token_str1.split("|")), token1)
        self.assertEqual(interpret_token(sentno, *token_str2.split("|")), token2)

        line = u"{token_str1}|hd/det|{token_str2}|{sentno}\n".format(**locals())

        sid, t1, t2, rel = interpret_line(line)

        self.assertEqual(sid, sentno)
        self.assertEqual(t1, token1)
        self.assertEqual(t2, token2)
        self.assertEqual(rel, "det")

    def test_parse(self):
        tokens, triples = Alpino(None).process_sentences(enumerate([u"ik zie h\xe9m!"]))
        self.assertEqual(len(tokens), 4, "Exptected 4 tokens, got %r" % tokens)
        self.assertIn(TokenValues(0, 3, "!", "!", ".", "punct", "uitroep", None), tokens)
        self.assertIn(TokenValues(0, 2, u"h\xe9m", u"hem", "O", "pronoun", "nwh,thi,sg,de,dat_acc,def", None), tokens)

        self.assertEqual(set(triples), {
                TripleValues(0, 0, 1, "su"),
                TripleValues(0, 2, 1, "obj1"),
                TripleValues(0, 3, 1, "--"),})

    def test_linebreak(self):
        tokens, triples = Alpino(None).process_sentences(enumerate([u"ik ga\nnaar huis"]))
        self.assertEqual(len(tokens), 4, "Exptected 4 tokens, got %r" % tokens)
        
    def test_unicode(self):
        def token_attr(tokens, position, attr="lemma"):
            return getattr([t for t in tokens if t.position==position][0], attr)
        tokens, triples = Alpino(None).process_sentences(enumerate([u"ik zie h\xe9m!"]))
        self.assertEqual(token_attr(tokens, 2, "word"), u"h\xe9m")
        self.assertEqual(token_attr(tokens, 2, "lemma"), u"hem")
        Alpino(None).process_sentences(enumerate(["dit is een van de leukste huizen"]))
        tokens, triples = Alpino(None).process_sentences(enumerate([u"het \u2018huis\u2019 kost \u20ac 100 \u2011 te duur?"]))
        self.assertEqual(token_attr(tokens, 1), u"'")
        self.assertEqual(token_attr(tokens, 7), u"te")

    def test_escape(self):
        tokens, triples = Alpino(None).process_sentences(
            enumerate([u"REPORTAGE | KLEIS JAGER | SEVRAN"]))
        self.assertEqual(len(tokens), 5) # KLEIS JAGER is one name

if __name__ == '__main__':
    from amcat.tools import amcatlogging
    amcatlogging.setup()
    a = Alpino(None)
    print a.process_sentences(list(enumerate(["dit is een test"])))
