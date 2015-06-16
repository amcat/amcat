##########################################################################
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
        l2 = Language.objects.create(label='zzz')
        o.add_label(l2, "blx")
        self.assertEqual(o.get_label(l2), "blx")
        self.assertEqual(o.label, "bla")

        # does .label and .get_label return a unicode object under all circumstances
        self.assertIsInstance(o.label, unicode)
        self.assertIsInstance(o.get_label(l2), unicode)


    def test_cache(self):
        """Are label lookups cached?"""
        l = Language.objects.create(label='zzz')
        o = amcattest.create_test_code(label="bla", extra_label="test", extra_language=l)
        with self.checkMaxQueries(0, "Get cached label"):
            self.assertEqual(o.get_label(l), "test")
        o = Code.objects.get(pk=o.id)
        with self.checkMaxQueries(1, "Get new label"):
            self.assertEqual(o.get_label(l), "test")
        with self.checkMaxQueries(0, "Get cached label"):
            self.assertEqual(o.get_label(l), "test")
        o = Code.objects.get(pk=o.id)
        o._cache_label(l, "onzin")
        with self.checkMaxQueries(0, "Get manually cached label"):
            self.assertEqual(o.get_label(l), "onzin")
