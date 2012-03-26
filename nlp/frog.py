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
Preprocess using ILK Frog
See http://ilk.uvt.nl/frog/ and
Van den Bosch, A., Busser, G.J., Daelemans, W., and Canisius, S., CLIN 2007.
"""

import telnetlib

from amcat.nlp.analysisscript import AnalysisScript, Token, Triple

class Frog(AnalysisScript):

    def __init__(self, analysis, host='localhost', port=12345, triples=False):
        super(Frog, self).__init__(analysis, triples=triples)
        self.host = host
        self.port = port

    @property
    def conn(self):
        try:
            return self._conn
        except AttributeError:
            self._conn = telnetlib.Telnet(self.host, self.port)
            return self._conn

    def _reset_connection(self):
        try:
            del self._conn
        except AttributeError:
            pass

    def preprocess_sentence(self, sentence):
        try:
            return list(self._do_process(sentence.sentence.encode("utf-8")))
        except:
            self._reset_connection()
            raise 
            
    def get_tokens(self, sentence, memo=None):
        if memo is None: memo = self.preprocess_sentence(sentence)
        for line in memo:
            position, word, lemma, pos = [line[i] for i in (0,1,2,4)]
            yield Token(sentence.id, int(position)-1, word, lemma, *read_pos(pos))

    def get_triples(self, sentence, memo=None):
        if memo is None: memo = self.preprocess_sentence(sentence)
        for line in memo:
            position, parent = [int(line[i]) for i in (0, -2)]
            if parent != 0:
                rel = line[-1]
                yield Triple(sentence.id, position-1, parent-1, rel)
            
            
    def _do_process(self, sentence):
        if type(sentence) != str: sentence = str(sentence)
        if not sentence.endswith("\n"):
            sentence += "\n"
        self.conn.write(sentence)
        result = self.conn.read_until("READY")
        result = result[:-len("READY")].strip()
        for line in result.split("\n"):
            if not line.strip(): continue
            yield line.split("\t")


FROG_POSMAP = {"VZ" : "P",
               "N" : "N",
               "ADJ" : "A",
               "LET" : ".",
               "VNW" : "O",
               "LID" : "D",
               "SPEC" : "M",
               "TW" : "Q",
               "WW" : "V",
               "BW" : "B",
               "VG" : "C",
               "TSW" : "I",
               "MWU" : "U",
               "" : "?",
               }
                  
def read_pos(pos):
    """Convert a frog pos string to a poscat, major, minor tuple"""
    pos = pos.split("_")[0]
    major, minor = pos.split("(")
    minor = minor.split(")")[0]
    poscat = FROG_POSMAP[major]
    return poscat, major, minor

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestFrog(amcattest.PolicyTestCase):
    def test_process_sentence(self):
        from amcat.models.sentence import Sentence
        s = Sentence(sentence="de groenste huizen")
        f = Frog(None)
        tokens, triples = f.process_sentence(s)
        tokens = list(tokens)
        lemmata = [token.lemma for token in tokens]
        self.assertEqual(lemmata, ["de", "groen", "huis"])
        poscats = [token.pos for token in tokens]
        self.assertEqual(poscats, ["D", "A", "N"])

    def test_read_pos(self):
        for input, poscat, major, minor in [
            ("BW()", "B", "BW", ""),
            ]:
            p, m, n = read_pos(input)
            self.assertEqual(p, poscat)
            self.assertEqual(m, major)
            self.assertEqual(n, minor)


    def test_triples(self):
        from amcat.models.sentence import Sentence
        s = Sentence(sentence="hij gaf hem een boek")
        f = Frog(None, triples=True, port=12346)
        triples = set(f.get_triples(s))
        self.assertEqual(triples, {Triple(s.id, 0, 1, 'su'),
                                   Triple(s.id, 2, 1, 'obj2'),
                                   Triple(s.id, 3, 4, 'det'),
                                   Triple(s.id, 4, 1, 'obj1'),
                                   })
                                   
        
        
        
        
