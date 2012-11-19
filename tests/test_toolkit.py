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

class TestToolkit(amcattest.PolicyTestCase):
    TARGET_MODULE = toolkit

    def test_ints2ranges(self):
        for i in range(10):
            seq = [random.randint(-100, 100) for dummy in range(100)]
            self.assertEqual(set(toolkit.flatten(range(fro, to+1) for (fro, to) in toolkit.ints2ranges(seq))), set(seq))
        for input, output in [
            ([0], [(0,0)]),
            ([], []),
            ]:
            self.assertEqual(list(toolkit.ints2ranges(input)), output)

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
            ("1980-3-22 01:00:00:00" , datetime.datetime(1980, 3, 22,0,0,0), False, True), #time->0
            ("1980-13-22 01:00:00:00" , None, False, True), # illegal date --> None
            ("1980-13-22 01:00:00" , ValueError, False, False), # illegal date --> Error
            ("1980-3-22 27:00:00" , ValueError, False, False), # illegal time --> Error
            ("1980-3-22 23:00:00:00" , ValueError, False, False), # illegal time --> Error
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
            self.assertEqual(toolkit.getYW(date), yw)
            self.assertEqual(toolkit.getYM(date), ym)
            self.assertEqual(toolkit.getYQ(date), yq)

    def test_pairs(self):
        for l, pairs in (
            ([1,2,3,4], [(1,2), (3,4)]),
            ([1,2,3,4,5], [(1,2), (3,4), (5,None)]),
            ((1,2,3,4,5), [(1,2), (3,4), (5,None)]),
            ):
            self.assertEqual(toolkit.pairs(l, lax=True), pairs)

    def test_getseq(self):
        for seq, result, stringok, convscal in (
            ([1,2,3], True, False, False),
            ((1,2,3), True, False, False),
            (set([6,5,4]), True, False, False),
            ((x for x in (1,2,3)), [1,2,3], False, False),
            ("bla", ["b","l","a"], True, False),
            ("bla", TypeError, False, False),
            ("bla", ["bla"], False, True),
            (1, [1], False, True),
            (1, [1], True, True),
            ):
            if inspect.isclass(result) and issubclass(result, Exception):
                self.assertRaises(result, toolkit.getseq, stringok=stringok, convertscalar=convscal)
            else:
                l2 = toolkit.getseq(seq, stringok=stringok, convertscalar=convscal)
                if result is True: self.assertTrue(seq is l2)
                else: self.assertEqual(l2, result)


    def test_execute(self):
        for cmd, input, output, error in (
            ("cat", "testje", "testje", ""),
            ("cat", None, "", ""),
            ("echo bla", None, "bla\n", ""),
            #("echo bla", "test", IOError, ""), # broken pipe, does not always raise...?
            ("cat 1>&2", "testje", "", "testje"),
            ):
            if inspect.isclass(output) and issubclass(output, Exception):
                self.assertRaises(output, toolkit.execute, cmd, input)
            else:
                out, err = toolkit.execute(cmd, input)
                self.assertEqual(out, output)
                self.assertEqual(err, error)
                if not error:
                    out = toolkit.execute(cmd, input, outonly=True)
                    self.assertEqual(out, output)

    def test_convert(self):
        PNG = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x03\x08\x02\x00\x00\x006\x88I\xd6\x00\x00\x00\tpHYs\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01\x95+\x0e\x1b\x00\x00\x00\x14IDAT\x08\x99c\xb4\xc8\x9f\xc6\xc0\xc0\xc0\xc4\xc0\xc0\x80\xa0\x00\x17}\x01CX\xc0\xa8\x0e\x00\x00\x00\x00IEND\xaeB`\x82'
        GIFSTART = 'GIF89a\x02\x00\x03\x00\xf0\x00\x008o\x96'
        out = toolkit.convertImage(PNG, 'png', 'gif')
        self.assertEqual(out[:len(GIFSTART)], GIFSTART)

    def test_splitlist(self):
        def plusone(l):
            for i,e in enumerate(l):
                l[i] = e+1
        for input, output, itemsperbatch, options in (
            ([1,2,3], [[1,2], [3]], 2, {}),
            ([1,2,3], [[1,2, 3]], 20, {}),
            ((1,2,3), [(1,2), (3,)], 2, {}),
            ([1,2,3], [[2,3], [4]], 2, dict(buffercall=plusone)),
            ((i for i in (1,2,3)), [[1,2],[3]], 2, {}),
            ((i for i in (1,2,3)), [1,2,3], 2, dict(yieldelements=True)),
            ((i for i in (1,2,3)), [2,3,4], 2, dict(buffercall=plusone,yieldelements=True)),

            ):
            o = toolkit.splitlist(input, itemsperbatch,  **options)
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

    def test_pad(self):
        for (seq, minlength, padwith, chop, padwithlast, out) in (
            ([1,2,3],  5, None, True, False, [1,2,3,None,None]),
            ([1,2,3],  1, None, True, False, [1]),
            ([1,2,3],  3, None, True, False, [1,2,3]),
            (range(4), 3, None, True, False, [0,1,2]),
            (range(2), 3, None, False,False, [0,1,None]),
            ((),       2, None, True, False, [None, None]),
            ([1,2],    0, None, True, False, []),
            ([1,2],    4, None, True, True, [1,2,2,2]),
            ((),       2, "test", True, True, ["test","test"]),
            ):
            self.assertEqual(list(toolkit.pad(seq, minlength, padwith, chop, padwithlast)), out)

    def test_zipp(self):
        for (seqs, zipped) in (
            (([1,2,3], [4,5,6]), [(1,4), (2,5), (3,6)]),
            (([1,2,3], [4,5]), ValueError),
            (([1], [4,5]), ValueError),
            ((), ()),
            (([1],), [(1,)]),
            ):
            if inspect.isclass(zipped) and issubclass(zipped, Exception):
                self.assertRaises(zipped, toolkit.zipp, *seqs)
            else:
                self.assertEqual(zipped, toolkit.zipp(*seqs))

    def test_hasattrv2(self):
        class A(object): pass
        class B(object): pass

        B.foo = 'bar'; A.B = B

        self.assertTrue(toolkit.hasattrv2(A, 'B.foo'))
        self.assertFalse(toolkit.hasattrv2(A, 'B.bar'))
        self.assertTrue(toolkit.hasattrv2(A, 'B'))
        self.assertFalse(toolkit.hasattrv2(A, 'C'))

    def test_getattrv2(self):
        class A(object): pass
        class B(object): pass

        B.foo = 'bar'; A.B = B

        self.assertEqual(toolkit.getattrv2(A, 'B.foo'), 'bar')
        self.assertEqual(toolkit.getattrv2(A, 'B'), B)
        self.assertRaises(AttributeError, toolkit.getattrv2, *(A, 'B.bar'))
        self.assertRaises(AttributeError, toolkit.getattrv2, *(A, 'C'))

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



    def test_retry(self):
        x = [3]
        def f():
            x[0] -= 1
            if x[0]: raise amcatlogging.SilentException("...")
            return 1

        with amcatlogging.collect() as log:
            self.assertEqual(toolkit.retry(f), 1)
        self.assertEqual(len(log), 2)

        x = [5]
        self.assertRaises(amcatlogging.SilentException, toolkit.retry, f)


    def test_set_closure(self):
        for (seed, function, expected) in [
            [[1], lambda x : [x+3] if x < 10 else [], {1, 4, 7, 10}],
            [{1, 8}, lambda x : [x+3] if x < 10 else [], {1, 4, 7, 8, 10, 11}],
            ]:
            result = toolkit.set_closure(seed, function)
            self.assertEqual(result, expected)

if __name__ == '__main__':
    amcattest.main()
