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
import os
import tempfile
import sys
import shutil
from amcat.models import PluginType
from amcat.tools import amcattest

from amcat.management.commands.sync_plugins import get_plugin_types, is_plugin, is_module, \
    get_plugin_type, get_plugins

class TestSyncPlugins(amcattest.AmCATTestCase):
    def test_get_plugin_types(self):
        all_types = set(p.get_class() for p in PluginType.objects.all())

        # Call two times to test caching
        self.assertEqual(all_types, set(get_plugin_types()))
        self.assertEqual(all_types, set(get_plugin_types()))

    def test_is_plugin(self):
        pclass = get_plugin_types()[0]
        class Test1(pclass): pass
        class Test2(object): pass

        self.assertFalse(is_plugin(pclass))
        self.assertTrue(is_plugin(Test1))
        self.assertFalse(is_plugin(Test2))

    def test_is_module(self):
        self.assertFalse(is_module("test/_bla.py"))
        self.assertFalse(is_module("test/_bla"))
        self.assertTrue(is_module("/"))
        self.assertTrue(is_module("/test.py"))
        self.assertFalse(is_module("/test.pyc"))
        self.assertFalse(is_module("/testpy"))

    def test_get_plugin_type(self):
        pt = PluginType.objects.all()[0]
        ptclass = pt.get_class()

        class Test1(ptclass): pass
        class Test2(object): pass

        self.assertEquals(get_plugin_type(Test1), pt)
        self.assertEquals(get_plugin_type(Test2), None)

    def _test_get_plugins(self, dir):
        testmod = os.path.join(dir, "test_module")
        os.mkdir(testmod)
        open(os.path.join(testmod, "__init__.py"), "w")

        self.assertEqual(set(), set(get_plugins([], plugin_module="plugin_test")))
        self.assertEqual(set(), set(get_plugins([testmod], plugin_module="plugin_test")))


    def test_get_plugins(self):
        root = tempfile.mkdtemp()

        try:
            # Create test-pacakge
            plugin_folder = os.path.join(root, "plugin_test")
            os.mkdir(plugin_folder)
            open(os.path.join(plugin_folder, "__init__.py"), "w")
            sys.path.append(root)
            self._test_get_plugins(plugin_folder)
        finally:
            shutil.rmtree(root)
            sys.path.remove(root)

