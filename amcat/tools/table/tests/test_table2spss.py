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
import datetime
import shutil
import unittest

from amcat.tools import amcattest
from amcat.tools.table import table3, table2spss


EXPECTED_ASCII_TABLE = """
DATA LIST LIST
 / a (F8.0) a_0 (DATETIME) a_1 (DOT9.2) a_2 (A255) .
BEGIN DATA.
1,01-JAN-2020-00:00:00,1.0,"test '  abc"
74321,01-JAN-2020-00:00:00,3.0,"abc this is a reeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeaaaaaaaaaaaaaaaaa"
4,01-JAN-2020-00:00:00,4.0,"asdf '"
END DATA.
list.
VARIABLE LABELS a 'a1' / a_0 'a2' / a_1 'a3' / a_2 'a4'.
SAVE OUTFILE='test.sav'.
"""

EXPECTED_UNICODE_TABLE = """
DATA LIST LIST
 / a (F8.0) a_0 (DATETIME) a_1 (DOT9.2) a_2 (A255) .
BEGIN DATA.
1,01-JAN-2020-00:00:00,1.0,"♝"
74321,01-JAN-2020-00:00:00,3.0,"♜"
4,01-JAN-2020-00:00:00,4.0,"✄"
END DATA.
list.
VARIABLE LABELS a 'a1' / a_0 'a2' / a_1 'a3' / a_2 'a4'.
SAVE OUTFILE='test.sav'.
"""

class TestTable2SPSS(amcattest.AmCATTestCase):
    def setUp(self):
        test_date = datetime.datetime(2020, 1, 1)

        self.ascii_data = [
            [1,     test_date, 1.0, "test '  abc"],
            [74321, test_date, 3.0, "abc this is a reeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaalllllly long string" ],
            [4,     test_date, 4.0, "asdf \""],
        ]

        self.unicode_data = [
            [1,     test_date, 1.0, "\u265d"],
            [74321, test_date, 3.0, "\u265c"],
            [4,     test_date, 4.0, "\u2704"],
        ]

        self.ascii_table = table3.ListTable(
            columnTypes=[int, datetime.datetime, float, str],
            colnames=["a1", "a2", "a3", "a4"],
            data=self.ascii_data
        )

        self.unicode_table = table3.ListTable(
            columnTypes=[int, datetime.datetime, float, str],
            colnames=["a1\u26f1", "a2\u26fd", "a3", "a4"],
            data=self.unicode_data
        )

    def test_asciitable2spss(self):
        spss_code = table2spss.table2spss(self.ascii_table, saveas="test.sav")
        self.assertEqual("".join(spss_code).strip(), EXPECTED_ASCII_TABLE.strip())

    def test_unitable2spss(self):
        spss_code = table2spss.table2spss(self.unicode_table, saveas="test.sav")
        self.assertEqual("".join(spss_code).strip(), EXPECTED_UNICODE_TABLE.strip())

    @unittest.skipUnless(shutil.which("pspp"), "PSPP not installed")
    def test_table2sav(self):
        print("".join(table2spss.table2spss(self.ascii_table, 'abc')))
        print(table2spss.table2sav(self.ascii_table))
