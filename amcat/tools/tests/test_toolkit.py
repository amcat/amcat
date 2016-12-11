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
from amcat.tools import amcattest, toolkit
import datetime

class TestToolkit(amcattest.AmCATTestCase):
    def test_splitlist(self):
        seq = [1, 2, 3, 4]

        # Test standard cases
        self.assertEqual(list(toolkit.splitlist([], 10)), [])
        self.assertEqual(list(toolkit.splitlist(seq, 1)), [[1], [2], [3], [4]])
        self.assertEqual(list(toolkit.splitlist(seq, 2)), [[1, 2], [3, 4]])
        self.assertEqual(list(toolkit.splitlist(seq, 3)), [[1, 2, 3], [4]])
        self.assertEqual(list(toolkit.splitlist(seq, 5)), [[1, 2, 3, 4]])

        # Errornous cases
        self.assertRaises(ValueError, lambda: list(toolkit.splitlist([], 0)))

        # Does it work for all iterables?
        self.assertEqual(list(toolkit.splitlist(iter(seq), 3)), [[1, 2, 3], [4]])

    def test_multidict(self):
        for input, output in (
                ([(1, 1), (1, 2), (1, 3), (2, 3)], {1: {1, 2, 3}, 2: {3}}),
                ((x for x in [(1, 1), (1, 2), (1, 3), (2, 3)]), {1: {1, 2, 3}, 2: {3}}),
                ((x for x in []), {}),
        ):
            self.assertEqual(dict(toolkit.multidict(input)), output)

    def test_strip_accents(self):
        test_string = "\xdf abc \xe7\xe3"
        self.assertEqual(toolkit.strip_accents(test_string), "ss abc ca")

    def test_readdate(self):
        for s, date in (
            ("22 maart 1980" , datetime.datetime(1980, 3, 22,0,0,0)),
            ("22 mrt 1980" , datetime.datetime(1980, 3, 22,0,0,0)),
            ("22/3/1980" , datetime.datetime(1980, 3, 22,0,0,0)),
            ("1980-3-22" , datetime.datetime(1980, 3, 22,0,0,0)),
            ("1980-3-22T01:00:05" , datetime.datetime(1980, 3, 22,1,0,5)),
            ("1980-3-22 01:00" , datetime.datetime(1980, 3, 22,1,0,0)),
            ("1980-3-22 01:00 PM" , datetime.datetime(1980, 3, 22,13,0,0)),
            ("1/1/98", datetime.datetime(1998, 1, 1,0,0,0)),
            ("1/1/04", datetime.datetime(2004, 1, 1,0,0,0)),
            ("31/12/72", datetime.datetime(1972, 12, 31,0,0,0)),
            ("1/2/1972", datetime.datetime(1972, 2, 1,0,0,0)),
            ("30.09.2008", datetime.datetime(2008, 9, 30,0,0,0)),
            ("31. Januar 2009", datetime.datetime(2009, 1, 31, 0, 0, 0)),
            ("March 31, 2003", datetime.datetime(2003, 3, 31, 0, 0, 0)),
            ("December 31, 2009 Thursday", datetime.datetime(2009, 12, 31, 0, 0, 0)),
            (u'30 ao\xfbt 2002', datetime.datetime(2002, 8, 30, 0, 0, 0)),
            ('31. Maerz 2003', datetime.datetime(2003, 3, 31, 0, 0, 0)),
            ('September 1, 2008 Monday 12:44 PM AEST', datetime.datetime(2008, 9, 1, 12, 44)),
            ('23aug2013', datetime.datetime(2013, 8, 23, 0, 0, 0)),
        ):
            date2 = toolkit.read_date(s)
            self.assertEqual(date2, date)

    def test_random_alphanum(self):
        self.assertEqual(len(toolkit.random_alphanum(1000)), 1000)
        self.assertEqual(len(toolkit.random_alphanum(100)), 100)
        self.assertEqual(len(toolkit.random_alphanum(80)), 80)
        self.assertEqual(len(toolkit.random_alphanum(60)), 60)
        self.assertNotEqual(toolkit.random_alphanum(100), toolkit.random_alphanum(100))