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

"""ORM Module representing scrapers"""

from django.db import models
from amcat.tools.model import AmcatModel
from amcat.tools import classtools
from amcat.tools.djangotoolkit import JsonField



class Plugin(AmcatModel):
    """A Plugin is a piece of code that provide a specific function that can
    be added 'at runtime'"""

    __label__ = 'label'

    id = models.AutoField(primary_key=True, db_column="plugin_id")

    module = models.CharField(max_length=100)
    class_name = models.CharField(max_length=100)
    label = models.CharField(max_length=100)
    description = models.TextField(null=True)
    type = models.ForeignKey("amcat.PluginType", null=True)

    arguments = JsonField(null=True, blank=False)
    active = models.BooleanField(default=True)

    class Meta():
        unique_together = (('module', 'class_name'),
                           ('type', 'label'),
                           )
        app_label = 'amcat'
        db_table = 'plugins'

    def get_class(self):
        """Return the class defined by this plugin"""
        return classtools.import_attribute(self.module, self.class_name)

    def get_instance(self, **options):
        """Return a new instance of this plugin using the options provided"""
        cls = self.get_class()

        _options = self.arguments or {}
        _options.update(options)
        return cls(**_options)

    @classmethod
    def can_create(cls, user):
        return user.haspriv('add_plugins')


class PluginType(AmcatModel):
    """A plugin type defines a type of plugins with a specific function

    A type has a plugin reference that points to the 'expected superclass' which is used
    to enumerate and/or check possible plugins. This creates a circular reference which is
    'solved' by making plugin.type nullable
    """

    id = models.AutoField(primary_key=True, db_column="plugintype_id")

    label = models.CharField(max_length=100)
    package = models.CharField(max_length=100)
    superclass = models.ForeignKey(Plugin)
    description = models.TextField()

    class Meta():
        app_label = 'amcat'
        db_table = 'plugintypes'

    def get_plugins(self, active=True, **options):
        """Return instances of all plugins of this type"""
        plugins = Plugin.objects.filter(type=self)
        if active is not None: plugins = plugins.filter(active=active)
        return (plugin.get_instance(**options) for plugin in plugins)

    def get_classes(self,  skip_existing_plugins=True):
        """
        Return the python classes in this type's package that are a subclass
        of the type superclass. Useful to enumerate possible plugins to
        register.
        """
        superclass = self.superclass.get_class()
        for cls in classtools.get_classes_from_package(self.package, superclass):
            if cls == superclass: continue
            if skip_existing_plugins:
                try:
                    Plugin.objects.get(class_name=cls.__name__, module=cls.__module__)
                except Plugin.DoesNotExist: pass
                else: continue # plugin existed
            yield cls

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

_X = 0
class _TestPlug(object):
    """Silly plugin class for testing"""
    @classmethod
    def create(cls, type=None, label=None):
        if label is None:
            global _X
            _X += 1
            label = "plugin_%i" % _X
        return Plugin.objects.create(label=label, module=cls.__module__,
                                     class_name=cls.__name__, type=type)

class _TestPlug1(_TestPlug):
    """Yet another silly plugin test class"""
    def __init__(self, a, b=2):
        self.a = a
        self.b = b

class _TestPlug2(_TestPlug1):
    """Yet another silly plugin test class"""

class _TestPlug3(_TestPlug):
    """Yet another silly plugin test class"""


class TestPlugin(amcattest.PolicyTestCase):

    def test_get_classes(self):
        spr = PluginType.objects.get(label="NLP Preprocessing")
        from amcat.nlp.frog import Frog
        from amcat.nlp.alpino import Alpino
        self.assertEqual(set([Frog, Alpino]) - set(spr.get_classes()), set())
        Plugin.objects.create(class_name="Frog", module="amcat.nlp.frog")
        self.assertNotIn(Frog, set(spr.get_classes()))
        self.assertIn(Frog, set(spr.get_classes(skip_existing_plugins=False)))


    def test_get_plugin(self):
        """Can we get a plugin object from the db?"""
        s = _TestPlug1.create()
        self.assertEqual(s.get_class(), _TestPlug1)
        self.assertRaises(TypeError, s.get_instance) # argument a missing
        self.assertEqual(s.get_instance(a=999).a, 999)      # argument via options

        s.arguments = dict(a=123, b="bla")
        s.save()
        s = Plugin.objects.get(pk=s.id)

        self.assertEqual(s.get_instance().a, 123)
        self.assertEqual(s.get_instance().b, "bla")
        self.assertEqual(s.get_instance(b=dict(x=set([1, 2, 3]))).b, {'x' : set([1, 2, 3])})

    def test_plugins_by_type(self):
        """Does getting plugins by type work correctly?"""
        spr = _TestPlug.create()
        a = PluginType.objects.create(superclass = spr)
        b = PluginType.objects.create(superclass = spr)
        _TestPlug1.create(type=a)
        _TestPlug2.create(type=a)
        s = _TestPlug3.create(type=b)

        self.assertEqual([x.__class__ for x in b.get_plugins()], [_TestPlug3])
        self.assertRaises(TypeError, list, a.get_plugins) # argument a missing
        self.assertEqual([x.__class__ for x in a.get_plugins(a=1)], [_TestPlug1, _TestPlug2])

        s.active = False
        s.save()
        self.assertEqual([x.__class__ for x in b.get_plugins()], [])

    def test_can_create(self):
        """Are only admins allowed to create new plugins??"""
        from amcat.models.authorisation import Role
        u = amcattest.create_test_user()
        self.assertFalse(Plugin.can_create(u))
        u.role = Role.objects.get(label="admin", projectlevel=False)
        u.save()
        self.assertTrue(Plugin.can_create(u))
