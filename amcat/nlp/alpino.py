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

CMD = "Alpino-amcat"
from amcat.tools import toolkit
from amcat.models.token import TokenValues, TripleValues
from amcat.models import AnalysisSentence

from amcat.nlp.analysisscript import VUNLPParser
from amcat.nlp import sbd, wordcreator

class AlpinoParser(VUNLPParser):
    parse_command = CMD

    def store_parse(self, analysed_article, data):
        analysis_sentences = {sentence.id : AnalysisSentence.objects.create(analysed_article=analysed_article, sentence=sentence).id
                              for sentence in sbd.get_or_create_sentences(analysed_article.article)}
        result = interpret_output(analysis_sentences, data)
        wordcreator.store_analysis(analysed_article, *result)

    def _sanitize(self, input):
        input = toolkit.stripAccents(input, latin1=True)
        input = input.replace("\n", " ")# alpino will stop parsing on line break
        input = input.replace("|", "-") # | is field separator and we don't care anyway
        input = input.encode('latin-1', 'ignore').decode('latin-1')
        return input

    def _get_text_to_submit(self, article):
        input = u"\n".join(u"{0}|{1}".format(sent.id, self._sanitize(sent.sentence))
                           for sent in self._get_sentences(article))
        if not input.endswith("\n"): input += "\n"
        return input

def interpret_output(sentences, data):
    tokens, triples = set(), []
    for line in data.split("\n"):
        if not line.strip(): continue
        parent, child, triple = interpret_line(sentences, line)
        tokens |= {parent, child}
        triples += [triple]
    return tokens, triples    
    
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


def interpret_line(sentences, line):
    data = line.split("|")
    if len(data) != 16:
        raise ValueError("Cannot interpret line %r, has %i parts (needed 16)" % (line, len(data)))
    sid = sentences[int(data[-1])]
    parent = interpret_token(sid, *data[:7])
    child = interpret_token(sid, *data[8:15])
    func, rel = data[7].split("/")

    triple = TripleValues(sid, child.position, parent.position, rel.strip())
    
    return parent, child, triple

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAlpino(amcattest.PolicyTestCase):

    def test_interpret(self):

        sentno = -124356789
        token_str1 = u"huis_DIM|huisje|1|2|noun|noun|noun(het,count,sg)"
        token_str2 = u"het|het|0|1|det|det(nwh)|determiner(het,nwh,nmod,pro,nparg,wkpro)"

        token1 = TokenValues(sentno, 1, "huisje", "huis_DIM", "N", "noun", "het,count,sg", None)
        token2 = TokenValues(sentno, 0, "het", "het", "D" ,"determiner", "het,nwh,nmod,pro,nparg,wkpro", None)


        self.assertEqual(interpret_token(sentno, *token_str1.split("|")), token1)
        self.assertEqual(interpret_token(sentno, *token_str2.split("|")), token2)

        line = u"{token_str1}|hd/det|{token_str2}|{sentno}\n".format(**locals())

        parent, child, triple = interpret_line(line)

        self.assertEqual(parent, token1)
        self.assertEqual(child, token2)
        self.assertEqual(triple.relation, "det")
        self.assertEqual(triple.parent, token1.position)
        self.assertEqual(triple.analysis_sentence, sentno)

        
###########################################################################
#                        U G L Y   C O N S T A N T                        #
###########################################################################

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
