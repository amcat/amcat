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
from amcat.tools.toolkit import import_attribute
from amcat.tools.model import AmcatModel
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
    type = models.CharField(max_length=100)

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
        return import_attribute(self.module, self.class_name)

    def get_instance(self, **options):
        """Return a new instance of this plugin using the options provided"""
        cls = self.get_class()

        _options = self.arguments or {}
        _options.update(options)
        return cls(**_options)

    @classmethod
    def can_create(cls, user):
        return user.haspriv('add_plugins')

def plugins_by_type(plugin_type, active=True, **options):
    """Return instances of all plugins matching the type"""
    plugins = Plugin.objects.filter(type=plugin_type)
    if active is not None: plugins = plugins.filter(active=active)
    return (plugin.get_instance(**options) for plugin in plugins)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class _TestPlug(object):
    """Silly plugin class for testing"""
    def __init__(self, a, b=2):
        self.a = a
        self.b = b

class _TestPlug2(object):
    """Yet another silly plugin test class"""

class TestPlugin(amcattest.PolicyTestCase):

    def test_get_plugin(self):
        """Can we get a plugin object from the db?"""

        s = Plugin.objects.create(module='amcat.models.plugin',
                                  class_name='_TestPlug')
        self.assertEqual(s.get_class(), _TestPlug)
        self.assertRaises(TypeError, s.get_instance) # argument a missing
        self.assertEqual(s.get_instance(a=999).a, 999)      # argument via options

        s.arguments = dict(a=123, b="bla")
        s.save()
        s = Plugin.objects.get(pk=s.id)

        self.assertEqual(s.get_instance().a, 123)
        self.assertEqual(s.get_instance().b, "bla")
        self.assertEqual(s.get_instance(b=dict(x={1, 2, 3})).b, {'x' : {1, 2, 3}})

    def test_plugins_by_type(self):
        """Does getting plugins by type work correctly?"""
        Plugin.objects.create(module='amcat.models.plugin', class_name='_TestPlug')
        Plugin.objects.create(module='amcat.models.plugin', class_name='_TestPlug', type='a')
        Plugin.objects.create(module='amcat.models.plugin', class_name='_TestPlug', type='a')
        s = Plugin.objects.create(module='amcat.models.plugin', class_name='_TestPlug2', type='b')

        self.assertEqual([x.__class__ for x in plugins_by_type('b')], [_TestPlug2])
        self.assertRaises(TypeError, list, plugins_by_type, 'a') # argument a missing
        self.assertEqual([x.__class__ for x in plugins_by_type('a', a=1)], [_TestPlug, _TestPlug])

        s.active = False
        s.save()
        self.assertEqual([x.__class__ for x in plugins_by_type('b')], [])

    def test_can_create(self):
        """Are only admins allowed to create new plugins??"""
        from amcat.models.authorisation import Role
        u = amcattest.create_test_user()
        self.assertFalse(Plugin.can_create(u))
        u.role = Role.objects.get(label="admin", projectlevel=False)
        u.save()
        self.assertTrue(Plugin.can_create(u))
