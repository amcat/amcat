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
from django.utils.functional import memoize
from functools import partial
from inspect import isclass
from itertools import imap, chain
from django.core.management.base import BaseCommand
from amcat.models import Plugin, PluginType
from amcat.contrib import plugins

import importlib
import os

import logging;
from amcat.tools.toolkit import cached

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

def _get_plugins(module_path):
    module_path = module_path[:-3] if module_path.endswith(".py") else module_path
    mod = importlib.import_module(".".join((PLUGIN_MODULE, os.path.basename(module_path))))
    attrs = (getattr(mod, a) for a in dir(mod) if not a.startswith('__'))
    return filter(is_plugin, attrs)

def get_qualified_name(cls):
    return cls.__module__ + "." + cls.__name__

def get_plugins(module_paths):
    """Return all classes which represent a plugin. Search modules `directories`."""
    return chain.from_iterable(imap(_get_plugins, module_paths))

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

class TestSyncPlugins(amcattest.PolicyTestCase):
    pass

