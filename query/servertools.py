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

import hashlib

PORT = 26221
KEYFILE1 = "/home/amcat/resources/key" # for amcat
KEYFILE2 = "/usr/home/netframe/resources/key" # for parc
KEY = None

REQUEST_LIST = 1
REQUEST_LIST_DISTINCT = 2
REQUEST_QUOTE = 3

FILTER_VALUES = 1
FILTER_INTERVAL = 2

def hash(s):
    global KEY
    if KEY is None:
        try:
            KEY = open(KEYFILE1).read()
        except IOError:
            KEY = open(KEYFILE2).read()
    return hashlib.md5(KEY+s).digest()

