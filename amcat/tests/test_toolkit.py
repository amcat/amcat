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
Test module for amcat.tools.toolkit
"""

from amcat.tools import toolkit, amcattest, amcatlogging
import datetime
import random
import inspect
import logging

class TestToolkit(amcattest.AmCATTestCase):
    TARGET_MODULE = toolkit

    def test_multidict(self):
        for input, output in (
            ([(1,1), (1,2), (1,3), (2,3)], {1 : set([1,2,3]), 2:set([3])}),
            ((x for x in [(1,1), (1,2), (1,3), (2,3)]), {1 : set([1,2,3]), 2:set([3])}),
            ((x for x in []), {}),
            ):
            self.assertEqual(dict(toolkit.multidict(input)), output)


    def test_readdate(self):
        for s, date, american, lax in (
            ("22 maart 1980" , datetime.datetime(1980, 3, 22,0,0,0), False, True),
            ("22 mrt 1980" , datetime.datetime(1980, 3, 22,0,0,0), False, True),
            ("22/3/1980" , datetime.datetime(1980, 3, 22,0,0,0), False, True),
            ("1980-3-22" , datetime.datetime(1980, 3, 22,0,0,0), False, True),
            ("1980-3-22T01:00:05" , datetime.datetime(1980, 3, 22,1,0,5), False, True),
            ("1980-3-22 01:00" , datetime.datetime(1980, 3, 22,1,0,0), False, True),
            ("1980-3-22 01:00 PM" , datetime.datetime(1980, 3, 22,13,0,0), False, True),
            ("1980-3-22 01:00:00:00" , datetime.datetime(1980, 3, 22,0,0,0), False, True), #time->0
            ("1980-13-22 01:00:00:00" , None, False, True), # illegal date --> None
            ("1980-13-22 01:00:00" , ValueError, False, False), # illegal date --> Error
            ("1980-3-22 27:00:00" , ValueError, False, False), # illegal time --> Error
            ("1980-3-22 23:00:00:00" , ValueError, False, False), # illegal time --> Error
            ("Sun Sep 29 18:21:12 +0000 2013", datetime.datetime(2013,9,29,18,21,12), False, False), # twitter (??)
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
            ):
            if inspect.isclass(date) and issubclass(date, Exception):
                self.assertRaises(date, toolkit.readDate, s, lax=False, american=american)
            else:
                date2 = toolkit.readDate(s, lax=lax, american=american)
                self.assertEqual(date2, date)


    def test_dateoutput(self):
        for date, iso, isotime, yw, ym, yq in (
            (datetime.datetime(1990, 1, 10, 13,1,0), "1990-01-10", "1990-01-10 13:01:00", 1990.02, 1990.01, 1990.1),
            ):
            self.assertEqual(toolkit.writeDate(date), iso)
            self.assertEqual(toolkit.writeDateTime(date), isotime)

    def test_splitlist(self):
        def plusone(l):
            for i,e in enumerate(l):
                l[i] = e+1
        for input, output, itemsperbatch in (
            ([1,2,3], [[1,2], [3]], 2),
            ([1,2,3], [[1,2, 3]], 20),
            ((1,2,3), [(1,2), (3,)], 2),
            ((i for i in (1,2,3)), [[1,2],[3]], 2),
            ):
            o = toolkit.splitlist(input, itemsperbatch)
            self.assertEqual(list(o), output)

    def test_sortbyvalue(self):
        for input, output in (
            ({"a" : 12, "b" : 6, "c" : 99}, [("b", 6), ("a" , 12), ("c", 99)]),
            ({"a" : 12, "b" : 6, "c" : 99}.items(), [("b", 6), ("a" , 12), ("c", 99)]),
            ({"a" : 12, "b" : 6, "c" : 99}.iteritems(), [("b", 6), ("a" , 12), ("c", 99)]),
            ):
            o = toolkit.sortByValue(input)
            self.assertEqual(o, output)

    def test_head(self):
        for input, filter, output in (
            ([1,2,3], None, 1),
            ([], None, None),
            ([1,2,3,4], lambda x : not x%2, 2),
            ([4,3,2,1], lambda x : not x%2, 4),
            ([3,1], lambda x : not x%2, None),

            ):
            self.assertEqual(output, toolkit.head(input, filter))
            self.assertEqual(output, toolkit.head(tuple(input), filter))
            self.assertEqual(output, toolkit.head((i for i in input), filter))
            s = set(input)
            out = toolkit.head(s, filter)
            if out is None:
                if filter:
                    self.assertTrue(not [x for x in s if filter(x)])
                else:
                    self.assertFalse(s)
            else:
                self.assertTrue(out in s, "%r not in %s" % (out, s))
                if filter:
                    self.assertTrue(filter(out))

    def test_to_list(self):
        @toolkit.to_list
        def gen(n):
            return (i for i in range(n))

        self.assertEqual(gen(n=12), list(range(12)))

    def test_wrapper(self):
        @toolkit.wrapped(sum)
        def gen(n):
            return (i for i in range(n))

        self.assertEqual(gen(n=3), sum(range(3)))

if __name__ == '__main__':
    amcattest.main()
