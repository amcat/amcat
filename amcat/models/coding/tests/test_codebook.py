###########################################################################
# (C) Vrije Universiteit, Amsterdam (the Netherlands)                     #
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

from amcat.models.coding.codebook import get_tree_levels

from amcat.models import Code, Codebook, CodebookCode, Language
from amcat.tools import amcattest
from django.core.exceptions import ObjectDoesNotExist

class TestCodebook(amcattest.AmCATTestCase):
    def test_create(self):
        """Can we create objects?"""
        c = amcattest.create_test_codebook()

        o = amcattest.create_test_code()
        co = c.add_code(o)
        co2 = c.add_code(Code.objects.create(), parent=o)

        self.assertIn(co, c.codebookcodes)
        #self.assertIn(o, c.codes)
        self.assertEqual(co2.parent, o)


    def standardize(self, codebook, **kargs):
        """return a dense hierarchy serialiseation for easier comparisons"""

        return ";".join(sorted(set("{0}:{1}".format(*cp)
                                   for cp in codebook.get_hierarchy(**kargs))))

    def test_hierarchy(self):
        """Does the code/parent base class resolution work"""
        a, b, c, d, e, f = [amcattest.create_test_code(label=l) for l in "abcdef"]


        # A: b (validto = 2010)
        #    +a
        #
        # a should have parent b, even when requesting hierarchy of 2013.
        Z = amcattest.create_test_codebook(name="Z")
        Z.add_code(code=b, validto=datetime.datetime(2010, 1, 1))
        Z.add_code(code=a, parent=b)
        tree = Z.get_tree(datetime.datetime(2013, 1, 1))
        self.assertEqual(tree[0].children[0].label, 'a')

        # A: a
        #    +b
        #     +c
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b, a)
        A.add_code(c, b)
        self.assertEqual(self.standardize(A), 'a:None;b:a;c:b')

        # D: d
        #    +e
        #    +f
        D = amcattest.create_test_codebook(name="D")
        D.add_code(d)
        D.add_code(e, d)
        D.add_code(f, d)
        self.assertEqual(self.standardize(D), 'd:None;e:d;f:d')

    def test_validation(self):
        """Test whether codebookcode validation works"""
        a, b, c, d = [amcattest.create_test_code(label=l) for l in "abcd"]
        A = amcattest.create_test_codebook(name="A")
        self.assertTrue(A.add_code(a, b, hide=True) is not None)

        # Delete code added in previous statement
        A.delete_codebookcode(CodebookCode.objects.get(codebook=A, code=a, parent=b))
        A.delete_codebookcode(CodebookCode.objects.get(codebook=A, code=b))

        self.assertRaises(ValueError, A.add_code, a, validfrom=datetime.datetime(2010, 1, 1),
                          validto=datetime.datetime(1900, 1, 1))
        A.add_code(a)
        A.add_code(b)
        A.add_code(c, a)
        self.assertRaises(ValueError, A.add_code, c, a)
        self.assertRaises(ValueError, A.add_code, c, b)
        self.assertRaises(ValueError, A.add_code, c, hide=True)

        A.add_code(d, a, validto=datetime.datetime(2010, 1, 1))
        A.add_code(d, b, validfrom=datetime.datetime(2010, 1, 1))

        self.assertRaises(ValueError, A.add_code, d, a)
        self.assertRaises(ValueError, A.add_code, d, a, validto=datetime.datetime(1900, 1, 1))
        self.assertRaises(ValueError, A.add_code, d, a, validfrom=datetime.datetime(1900, 1, 1))

        # different code book should be ok
        B = amcattest.create_test_codebook(name="B")
        B.add_code(a)
        B.add_code(c, a)


    def test_get_timebound_functions(self):
        """Test whether time-bound functions are returned correctly"""
        a, b, c = [amcattest.create_test_code(label=l) for l in "abc"]
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(c, a, validfrom=datetime.datetime(2010, 1, 1))
        self.assertEqual(self.standardize(A), 'a:None;c:a')
        self.assertEqual(self.standardize(A, date=datetime.datetime(1900, 1, 1)), 'a:None')
        A.add_code(b)
        A.add_code(c, b, validto=datetime.datetime(2010, 1, 1))
        self.assertEqual(self.standardize(A, date=datetime.datetime(2009, 12, 31)), 'a:None;b:None;c:b')
        self.assertEqual(self.standardize(A, date=datetime.datetime(2010, 1, 1)), 'a:None;b:None;c:a')
        self.assertEqual(self.standardize(A, date=datetime.datetime(2010, 1, 2)), 'a:None;b:None;c:a')


    def test_codes(self):
        """Test the codes property"""
        a, b, c, d = [amcattest.create_test_code(label=l) for l in "abcd"]

        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b, a)
        A.add_code(c, a, validfrom=datetime.datetime(1910, 1, 1), validto=datetime.datetime(1920, 1, 1))

        self.assertEqual(set(A.codes), {a, b, c})

        B = amcattest.create_test_codebook(name="B")

        B.add_code(d, b)
        self.assertEqual(set(B.codes), {d, b})

    def test_add_codes(self):
        a, b, c, d, e = [amcattest.create_test_code(label=l) for l in "abcde"]

        A = amcattest.create_test_codebook(name="A")

        A.add_codes([a])
        self.assertTrue(A._code_in_codebook(a))

        A.add_codes([(b, c)])
        self.assertTrue(A._code_in_codebook(b))
        self.assertTrue(A._code_in_codebook(c))

        A.add_codes([(d, c)])
        self.assertTrue(A._code_in_codebook(d))
        self.assertTrue(A._code_in_codebook(c))

        A.add_codes([(e, None)])
        self.assertTrue(A._code_in_codebook(e))

        self.assertRaises(ValueError, A.add_codes, [e])
        self.assertRaises(ValueError, A.add_codes, [(e, b)])


    def test_codebookcodes(self):
        """Test the get_codebookcodes function"""

        def _copairs(codebook, code):
            """Get (child, parent) pairs for codebookcodes"""
            for co in codebook.get_codebookcodes(code):
                yield co.code, co.parent


        a, b, c, d, e = [amcattest.create_test_code(label=l) for l in "abcde"]

        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b)
        A.add_code(c, a, validfrom=datetime.datetime(1910, 1, 1), validto=datetime.datetime(1920, 1, 1))
        A.add_code(c, b, validfrom=datetime.datetime(1920, 1, 1), validto=datetime.datetime(1930, 1, 1))
        A.add_code(d, a)
        A.add_code(e, a)

        self.assertEqual(set(_copairs(A, a)), {(a, None)})
        self.assertEqual(set(_copairs(A, c)), {(c, a), (c, b)})
        self.assertEqual(set(_copairs(A, d)), {(d, a)})
        self.assertEqual(set(_copairs(A, e)), {(e, a)})

        B = amcattest.create_test_codebook(name="B")
        B.add_code(d, b)
        B.add_code(e, b, validfrom=datetime.datetime(2012, 1, 1))

    def test_roots_children(self):
        """Does getting the roots and children work?"""
        a, b, c, d, e, f = [amcattest.create_test_code(label=l) for l in "abcdef"]

        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b)
        A.add_code(e, a)
        A.add_code(d, c)
        A.add_code(f, a)

        self.assertEqual(set(A.get_roots()), {a, b, c})
        self.assertEqual(set(A.get_children(a)), {e, f})
        self.assertEqual(set(A.get_children(c)), {d})
        self.assertEqual(set(A.get_children(d)), set())

    def test_get_ancestors(self):
        a, b, c, d, e, f = [amcattest.create_test_code(label=l) for l in "abcdef"]
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b)
        A.add_code(c, b)
        A.add_code(e, a)
        A.add_code(d, c)
        A.add_code(f, a)
        self.assertEqual(list(A.get_ancestor_ids(f.id)), [f.id, a.id])
        self.assertEqual(list(A.get_ancestor_ids(a.id)), [a.id])
        B = amcattest.create_test_codebook(name="B")
        B.add_code(f, b)

    @amcattest.require_postgres
    def test_caching_correctness(self):
        """
        Each method gets decorated with {cache, cache_labels, cache+cache_labels} after which
        each of the tests above is re-run.
        """
        cached_functions = {"get_codebookcodes", "get_codebookcode", "_get_hierarchy_ids", "get_tree", "get_hierarchy",
                            "get_code_ids", "get_codes", "get_code", "add_code", "add_base", "get_roots",
                            "get_children", "get_ancestor_ids"}

        caching_functions = {"cache", "cache_labels", "invalidate_cache"}

        def _getattr(orig):
            def wrapped(self, name):
                if name in cached_functions:
                    self.cache()
                return orig(self, name)

            return wrapped

        ga = Codebook.__getattribute__
        Codebook.__getattribute__ = _getattr(ga)

        try:
            self.test_create()
            self.test_hierarchy()
            self.test_validation()
            self.test_get_timebound_functions()
            self.test_codes()
            self.test_codebookcodes()
            self.test_roots_children()
            self.test_get_ancestors()
            self.test_add_codes()
            self.test_ordering()
        finally:
            Codebook.__getattribute__ = ga

    def test_cache_labels_language(self):
        """Does caching labels for multiple language work
        esp. caching non-existence of a label"""
        from amcat.models.language import Language

        l1 = Language.objects.get(pk=1)
        a = amcattest.create_test_code(extra_label="a", extra_language=l1)
        l2 = Language.objects.get(pk=2)
        b = amcattest.create_test_code(extra_label="b", extra_language=l2)
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b)

        with self.checkMaxQueries(3, "Cache labels"):
            # 1 for "normal" caching, and 1 for each cache_labels()
            A.cache_labels(l1)
            A.cache_labels(l2)

        # Codebooks must export _lables, which is a dictionary which
        # contains all the cached labels.
        self.assertEqual(A._labels[a.id][l1.id], "a")
        self.assertEqual(A._labels[b.id][l2.id], "b")

        A.invalidate_cache()
        with self.checkMaxQueries(2, "Cache labels"):
            A.cache_labels(l1, l2)

        with self.checkMaxQueries(0, "Get cached codes"):
            a, b = map(A.get_code, [a.id, b.id])

        with self.checkMaxQueries(0, "Get multiple cached codes"):
            list(A.get_codes())

        with self.checkMaxQueries(0, "Get exisitng labels"):
            self.assertEqual(a.get_label(l1), "a")
            self.assertEqual(b.get_label(l2), "b")

        with self.checkMaxQueries(0, "Get non-existing labels"):
            self.assertRaises(ObjectDoesNotExist, a.get_label, l2)

        with self.checkMaxQueries(0, "Get tree"):
            list(A.get_tree())

        c = amcattest.create_test_code(label="c")
        with self.checkMaxQueries(5, "Add new code"):
            A.add_code(c)

    def test_ordering(self):
        """
        Codebookcodes should always be returned in order, according
        to their codenr-property (see CodebookCode.codenr).
        """
        cb = amcattest.create_test_codebook()
        code_a, code_b, code_c = (amcattest.create_test_code() for i in range(3))

        ccode_c = cb.add_code(code_c, ordernr=3)
        ccode_b = cb.add_code(code_b, ordernr=2)
        ccode_a = cb.add_code(code_a, ordernr=1)

        cb.invalidate_cache()

        # These tests will automatically be run with caching enabled by
        # the method test_caching_correctness()
        self.assertEquals(tuple(cb.codebookcodes), (ccode_a, ccode_b, ccode_c))
        roots = [ti.code_id for ti in cb.get_tree()]
        self.assertEquals(roots, [code_a.id, code_b.id, code_c.id])

        # Test again with differnt order
        ccode_b.ordernr = 256
        ccode_b.save()
        cb.invalidate_cache()

        self.assertEquals(tuple(cb.codebookcodes), (ccode_a, ccode_c, ccode_b))
        roots = [ti.code_id for ti in cb.get_tree()]
        self.assertEquals(roots, [code_a.id, code_c.id, code_b.id])

    def test_get_descendants(self):
        a, b, c, d, e, f,g = [amcattest.create_test_code(label=l) for l in "abcdefg"]

        # D: d
        #    +e
        #    +f
        #    ++g
        #    a
        #    b
        #    +c
        D = amcattest.create_test_codebook(name="D")
        D.add_code(d)
        D.add_code(e, d)
        D.add_code(f, d)
        D.add_code(g, f)
        D.add_code(a)
        D.add_code(b)
        D.add_code(c, b)

        tree = D.get_tree()

        a = next(t for t in tree if t.label == "a")
        b = next(t for t in tree if t.label == "b")
        d = next(t for t in tree if t.label == "d")

        self.assertEqual({t.code_id for t in a.get_descendants()}, set())
        self.assertEqual({t.code_id for t in b.get_descendants()}, {c.id})
        self.assertEqual({t.code_id for t in d.get_descendants()}, {e.id, f.id, g.id})


    def test_get_aggregation_mapping(self):
        a, b, c, d, e, f,g = [amcattest.create_test_code(label=l) for l in "abcdefg"]

        # D: d
        #    +e
        #    +f
        #    ++g
        #    a
        #    b
        #    +c
        D = amcattest.create_test_codebook(name="D")
        D.add_code(d)
        D.add_code(e, d)
        D.add_code(f, d)
        D.add_code(g, f)
        D.add_code(a)
        D.add_code(b)
        D.add_code(c, b)

        # Codebook not cached
        self.assertRaises(ValueError, D.get_aggregation_mapping)
        D.cache()

        # Codebook cached
        self.assertEqual({u'c': u'b', u'e': u'd', u'f': u'd'}, D.get_aggregation_mapping())

    def test_get_language_ids(self):
        al, bl, cl = [Language.objects.create(label=l) for l in "abc"]
        ac, bc, cc = [amcattest.create_test_code(label=l) for l in "abc"]

        ac.add_label(al, "a")
        bc.add_label(bl, "a")
        cc.add_label(cl, "a")

        A = amcattest.create_test_codebook(name="A")

        A.add_code(ac)
        A.add_code(bc)
        A.add_code(cc)

        self.assertEqual(A.get_language_ids(), {al.id, bl.id, cl.id})

    def test_get_tree_levels(self):
        a, b, c, d, e, f,g = [amcattest.create_test_code(label=l) for l in "abcdefg"]

        # D: d
        #    +e
        #    +f
        #    ++g
        #    a
        #    b
        #    +c
        D = amcattest.create_test_codebook(name="D")
        D.add_code(d)
        D.add_code(e, d)
        D.add_code(f, d)
        D.add_code(g, f)
        D.add_code(a)
        D.add_code(b)
        D.add_code(c, b)

        tree = D.get_tree()

        levels = get_tree_levels(tree)
        level0 = next(levels)
        level1 = next(levels)
        level2 = next(levels)

        self.assertRaises(StopIteration, next, levels)
        self.assertEqual({d.id, a.id, b.id}, {ti.code_id for ti in level0})
        self.assertEqual({e.id, f.id, c.id}, {ti.code_id for ti in level1})
        self.assertEqual({g.id},             {ti.code_id for ti in level2})

        empty = amcattest.create_test_codebook(name="empty")
        levels = get_tree_levels(empty.get_tree())
        self.assertRaises(StopIteration, next, levels)
