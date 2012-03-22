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




def process_sentences(sentences):
    t = telnetlib.Telnet("localhost", 12345)
    for sentence in sentences:
        try:
            _sent_sentence(t, sentence)
            


t = telnetlib.Telnet("localhost", 12345)

print("> connected, sending...")
t.write("de katjes liepen door het gras\n")
print("> sent, receiving...")
print t.read_until("READY")
print "---------"
t.write("toen gingen we naar 't huis terug\n")
print t.read_until("READY")

t.close()


