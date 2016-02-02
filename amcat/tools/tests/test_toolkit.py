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
from __future__ import absolute_import
from amcat.tools import amcattest
from amcat.tools.toolkit import splitlist


class TestToolkit(amcattest.AmCATTestCase):
    def test_splitlist(self):
        seq = [1, 2, 3, 4]

        # Test standard cases
        self.assertEqual(list(splitlist([], 10)), [])
        self.assertEqual(list(splitlist(seq, 1)), [[1], [2], [3], [4]])
        self.assertEqual(list(splitlist(seq, 2)), [[1, 2], [3, 4]])
        self.assertEqual(list(splitlist(seq, 3)), [[1, 2, 3], [4]])
        self.assertEqual(list(splitlist(seq, 5)), [[1, 2, 3, 4]])

        # Errornous cases
        self.assertRaises(ValueError, lambda: list(splitlist([], 0)))

        # Does it work for all iterables?
        self.assertEqual(list(splitlist(iter(seq), 3)), [[1, 2, 3], [4]])
