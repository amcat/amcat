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

class Frog(object):

    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
    
    @property
    def conn(self):
        try:
            return self._conn
        except AttributeError:
            self._conn = telnetlib.Telnet(self.host, self.port)
            return self._conn

    def _reset_connection(Self):
        try:
            del self._conn
        except AttributeError:
            pass
        
    def process_sentences(self, sentences):
        for sentenceid, sentence in sentences:
            try:
                tokens = list(self.process_sentence(sentence))
            except:
                log.exception("Error on processing %i: %r" % (sentenceid, sentence))
                self._reset_connection()
            else:
                for token in tokens:
                    yield sentenceid, token
            
    def process_sentence(self, sentence):
        for line in self._do_process(sentence):
            position, word, lemma, pos = [line[i] for i in (0,1,2,4)]
            yield (int(position)-1, word, lemma) + read_pos(pos)
            
    def _do_process(self, sentence):
        if not sentence.endswith("\n"):
            sentence += "\n"
        self.conn.write(sentence)
        result = self.conn.read_until("READY")
        result = result[:-len("READY")].strip()
        for line in result.split("\n"):
            if not line.strip(): continue
            yield line.split("\t")


TADPOLE_POSMAP = {"VZ" : "P",
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
    major, minor = pos.split("(")
    minor = minor.split(")")[0]
    poscat = TADPOLE_POSMAP[major]
    return poscat, major, minor

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestFrog(amcattest.PolicyTestCase):
    def test_process_sentence(self):
        f = Frog()
        tokens = list(f.process_sentence("de groenste huizen"))
        lemmata = [token[2] for token in tokens]
        self.assertEqual(lemmata, ["de", "groen", "huis"])
        poscats = [token[3] for token in tokens]
        self.assertEqual(poscats, ["D", "A", "N"])

    def test_read_pos(self):
        for input, poscat, major, minor in [
            ("BW()", "B", "BW", ""),
            ]:
            p, m, n = read_pos(input)
            self.assertEqual(p, poscat)
            self.assertEqual(m, major)
            self.assertEqual(n, minor)
