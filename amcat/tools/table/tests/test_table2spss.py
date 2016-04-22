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
import subprocess

from amcat.tools import amcattest
from amcat.tools.table import table3, table2spss


"""
DATA LIST FREE
"""

class TestTable2SPSS(amcattest.AmCATTestCase):
    def setUp(self):
        test_date_1 = datetime.datetime(2020, 9, 8)
        test_date_2 = datetime.datetime(2015, 7, 6)
        test_date_3 = datetime.datetime(2010, 5, 4)

        self.ascii_data = [
            [1,     test_date_1, 1.0, "test '  abc"],
            [74321, test_date_2, 3.0, "abc\n this is a really string"*100],
            [4,     test_date_3, 4.0, "asdf \""],
        ]

        self.unicode_data = [
            [1,     test_date_1, 1.0, "\u265d"],
            [74321, test_date_2, 3.0, "\u265c"],
            [4,     test_date_3, 4.0, "\u2704"],
            [5,     test_date_1, 5.0, "\u2704"],
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

    def test_asciitable2sav(self):
        file = table2spss.table2sav(self.ascii_table)

        pspp = subprocess.Popen(
            ["pspp", "-b"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        input = b"get file='%s'.\nlist.\nshow n.\n" % file.encode("utf-8")
        stdout, stderr = pspp.communicate(input=input, timeout=30)
        self.assertIn(b"N is 3.", stdout)
        self.assertIn(b"74321", stdout)
        # Testing dates isn't really possible due to strange formatting due to long lines..


    def test_unitable2sav(self):
        file = table2spss.table2sav(self.unicode_table)

        pspp = subprocess.Popen(
            ["pspp", "-b"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        input = b"get file='%s'.\nlist.\nshow n.\n" % file.encode("utf-8")
        stdout, stderr = pspp.communicate(input=input, timeout=30)
        print(stdout)
        self.assertIn(b"N is 4.", stdout)
        self.assertIn(b"08-SEP-2020 00:00:00", stdout)
        self.assertIn(b"06-JUL-2015 00:00:00", stdout)
        self.assertIn(b"04-MAY-2010 00:00:00", stdout)
        self.assertIn(b"74321", stdout)
        self.assertIn("♜".encode("utf-8"), stdout)
        self.assertIn("♝".encode("utf-8"), stdout)
        self.assertIn("✄".encode("utf-8"), stdout)

