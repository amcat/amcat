# ##########################################################################
# (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
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
Test module for amcat.tools.toolkit
"""

import datetime
import inspect

from amcat.tools import toolkit, amcattest
from amcat.tools.toolkit import wrapped


class TestToolkit(amcattest.AmCATTestCase):
    TARGET_MODULE = toolkit

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
        for s, date, american, lax in (
            ("22 maart 1980" , datetime.datetime(1980, 3, 22,0,0,0), False, True),
            ("22 mrt 1980" , datetime.datetime(1980, 3, 22,0,0,0), False, True),
            ("22/3/1980" , datetime.datetime(1980, 3, 22,0,0,0), False, True),
            ("1980-3-22" , datetime.datetime(1980, 3, 22,0,0,0), False, True),
            ("1980-3-22T01:00:05" , datetime.datetime(1980, 3, 22,1,0,5), False, True),
            ("1980-3-22 01:00" , datetime.datetime(1980, 3, 22,1,0,0), False, True),
            ("1980-3-22 01:00 PM" , datetime.datetime(1980, 3, 22,13,0,0), False, True),
            ("1/1/98", datetime.datetime(1998, 1, 1,0,0,0), False, True),
            ("1/1/04", datetime.datetime(2004, 1, 1,0,0,0), False, True),
            ("31/12/72", datetime.datetime(1972, 12, 31,0,0,0), False, True),
            ("12/31/72", datetime.datetime(1972, 12, 31,0,0,0), True, True),
            ("1/2/1972", datetime.datetime(1972, 2, 1,0,0,0), False, True),
            ("1/2/1972", datetime.datetime(1972, 1, 2,0,0,0), True, True),
            ("1/2/1972", datetime.datetime(1972, 1, 2,0,0,0), True, True),
            ("30.09.2008", datetime.datetime(2008, 9, 30,0,0,0), False, False),
            ("31. Januar 2009", datetime.datetime(2009, 1, 31, 0, 0, 0), False, True),
            ("December 31, 2009 Thursday", datetime.datetime(2009, 12, 31, 0, 0, 0), False, False),
            (u'30 ao\xfbt 2002', datetime.datetime(2002, 8, 30, 0, 0, 0), False, False),
            ('31. Maerz 2003', datetime.datetime(2003, 3, 31, 0, 0, 0), False, False),
            ('September 1, 2008 Monday 12:44 PM AEST', datetime.datetime(2008, 9, 1, 12, 44), False, False),
            ('23aug2013', datetime.datetime(2013, 8, 23, 0, 0, 0), False, False),
        ):

            if inspect.isclass(date) and issubclass(date, Exception):
                self.assertRaises(date, toolkit.read_date, s, lax=False, american=american)
            else:
                date2 = toolkit.read_date(s, lax=lax, american=american)
                self.assertEqual(date2, date)

    def test_head(self):
        it = iter(range(10))
        self.assertEqual(0, toolkit.head(it))
        self.assertEqual(1, toolkit.head([1, 2]))

    def test_to_list(self):
        @wrapped(list)
        def gen(n):
            return (i for i in range(n))

        self.assertEqual(gen(n=12), list(range(12)))

    def test_wrapper(self):
        @toolkit.wrapped(sum)
        def gen(n):
            return (i for i in range(n))

        self.assertEqual(gen(n=3), sum(range(3)))

