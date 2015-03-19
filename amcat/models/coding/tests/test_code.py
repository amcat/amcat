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
from __future__ import print_function, unicode_literals

from amcat.models import Code
from amcat.models import Language
from amcat.tools import amcattest


class TestCode(amcattest.AmCATTestCase):
    def test_label(self):
        """Can we create objects and assign labels?"""
        # simple label
        o = amcattest.create_test_code(label="bla")
        self.assertEqual(o.label, "bla")
        self.assertEqual(unicode(o), o.label)
        # fallback with 'unknown' language
        l2 = Language.objects.create(label='zzz')
        self.assertEqual(o.get_label(l2), "bla")
        # second label
        o.add_label(l2, "blx")
        self.assertEqual(o.get_label(l2), "blx")
        self.assertEqual(o.get_label(Language.objects.create()), "bla")
        self.assertEqual(o.label, "bla")

        # does .label return something sensible on objects without labels?
        o2 = Code.objects.create()
        self.assertIsInstance(o2.label, unicode)
        self.assertRegexpMatches(o2.label, r'^<Code: \d+>$')
        self.assertIsNone(o2.get_label(l2))

        # does .label and .get_label return a unicode object under all circumstances
        self.assertIsInstance(o.label, unicode)
        self.assertIsInstance(o.get_label(l2), unicode)
        self.assertIsInstance(o2.label, unicode)

    def test_all_labels_cached(self):
        l = Language.objects.create(label='zzz')
        o = amcattest.create_test_code(label="bla", language=l)
        o = Code.objects.get(id=o.id)
        o._all_labels_cached = True

        with self.checkMaxQueries(0, "Getting non-existing label with _all_cached=True"):
            self.assertEqual(o.get_label(5), None)

        with self.checkMaxQueries(0, "Getting label with _all_cached=True"):
            self.assertEqual(o.label, "<Code: {id}>".format(id=o.id))

        o._cache_label(l, "bla2")
        self.assertEqual(o.get_label(5), "bla2")

        o = Code.objects.get(id=o.id)
        self.assertEqual(o.label, "bla")

        # If all labels are cached, and _labelcache contains codes with None and
        # a code with a string, get_label should return the string
        o._labelcache = {1: None, 2: "grr"}
        o._all_labels_cached = True

        self.assertEqual(o.label, "grr")
        self.assertEqual(o.get_label(3, fallback=True), "grr")
        self.assertEqual(o.get_label(2, fallback=False), "grr")
        self.assertEqual(o.get_label(1, fallback=True), "grr")


    def test_cache(self):
        """Are label lookups cached?"""
        l = Language.objects.create(label='zzz')
        o = amcattest.create_test_code(label="bla", language=l)
        with self.checkMaxQueries(0, "Get cached label"):
            self.assertEqual(o.get_label(l), "bla")
        o = Code.objects.get(pk=o.id)
        with self.checkMaxQueries(1, "Get new label"):
            self.assertEqual(o.get_label(l), "bla")
        with self.checkMaxQueries(0, "Get cached label"):
            self.assertEqual(o.get_label(l), "bla")
        o = Code.objects.get(pk=o.id)
        o._cache_label(l, "onzin")
        with self.checkMaxQueries(0, "Get manually cached label"):
            self.assertEqual(o.get_label(l), "onzin")
