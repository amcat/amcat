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
from functools import partial
from django.utils.functional import memoize
from inspect import isclass
from itertools import imap, chain
from django.core.management.base import BaseCommand
from amcat.models import Plugin, PluginType
from amcat.contrib import plugins

import importlib
import os

import logging
log = logging.getLogger(__name__)


PLUGIN_MODULE = plugins.__name__

def get_plugin_types():
    """Return all classes which represent a plugintype"""
    return tuple(p.get_class() for p in PluginType.objects.all())
get_plugin_types = memoize(get_plugin_types, {}, 0)

def is_plugin(cls):
    """Determines whether given class represents a plugin.

    @type return: bool"""
    return (isclass(cls) and issubclass(cls, get_plugin_types())) and cls not in get_plugin_types()

def is_module(path):
    """
    Returns True if this path seems to be a Python file (and does not start with an
    underscore) or is a directory (assumed to be a package).
    """
    return (
        # Is a Python file, and not private
        (not os.path.basename(path).startswith("_") and path.endswith(".py"))
        # Or is package
        or os.path.isdir(path)
    )

def _get_plugins(module_path, plugin_module):
    module_path = module_path[:-3] if module_path.endswith(".py") else module_path
    mod = importlib.import_module(".".join((plugin_module, os.path.basename(module_path))))
    attrs = (getattr(mod, a) for a in dir(mod) if not a.startswith('__'))
    return filter(is_plugin, attrs)

def get_plugins(module_paths, plugin_module=PLUGIN_MODULE):
    """Return all classes which represent a plugin. Search modules `directories`."""
    return chain.from_iterable(imap(partial(_get_plugins, plugin_module=plugin_module), module_paths))

def get_qualified_name(cls):
    return cls.__module__ + "." + cls.__name__

def get_plugin_type(cls):
    """Returns PluginType instance based on given class."""
    for pt in get_plugin_types():
        if issubclass(cls, pt):
            return PluginType.objects.get(class_name=get_qualified_name(pt))

class Command(BaseCommand):
    help = 'Syncs plugins available in amcat.contrib.plugins, and plugins currently in database.'

    def handle(self, *args, **options):
        # Remove plugins which yield an error upon importing
        for plugin in Plugin.objects.all():
            try:
                plugin.get_class()
            except ImportError:
                while True:
                    ans = raw_input('Error on importing {plugin.class_name}. Remove? [y/N]'.format(**locals()))
                    ans = ans.strip().lower()

                    if ans in ("", "n"):
                        break
                    elif ans == "y":
                        plugin.delete()
                        break

        # Look for plugins in plugin directory
        plugin_files = os.listdir(os.path.dirname(plugins.__file__))
        plugin_paths = (os.path.join(os.path.dirname(plugins.__file__), p) for p in plugin_files)
        detected_plugins = get_plugins(filter(is_module, plugin_paths))
        new_plugins = (p for p in detected_plugins if not Plugin.objects.filter(class_name=get_qualified_name(p)).exists())

        for p in new_plugins:
            log.info("Found new plugin: {p}".format(**locals()))

            plugin = Plugin.objects.create(
                label=p.name(),
                class_name=get_qualified_name(p),
                plugin_type=get_plugin_type(p)
            )

            log.info("Created new plugin: {plugin.class_name}".format(**locals()))


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

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
        import tempfile

        testmod = os.path.join(dir, "test_module")
        os.mkdir(testmod)
        open(os.path.join(testmod, "__init__.py"), "w")

        self.assertEqual(set(), set(get_plugins([], plugin_module="plugin_test")))
        self.assertEqual(set(), set(get_plugins([testmod], plugin_module="plugin_test")))


    def test_get_plugins(self):
        import tempfile
        import shutil
        import sys

        try:
            # Create test-pacakge
            root = tempfile.mkdtemp()
            plugin_folder = os.path.join(root, "plugin_test")
            os.mkdir(plugin_folder)
            open(os.path.join(plugin_folder, "__init__.py"), "w")
            sys.path.append(root)
            self._test_get_plugins(plugin_folder)
        finally:
            shutil.rmtree(root)
            sys.path.remove(root)


