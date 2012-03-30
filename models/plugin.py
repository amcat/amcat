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
        app_label = 'amcat'
        db_table = 'plugins'

    def get_class(self):
        return import_attribute(self.module, self.class_name)

    def get_instance(self, **options):
        cls= self.get_class()

        _options = self.arguments or {}
        _options.update(options)
        return cls(**_options)

def plugins_by_type(type, active=True, **options):
    plugins = Plugin.objects.filter(type=type)
    if active is not None: plugins = plugins.filter(active=active)
    return [plugin.get_instance(**options) for plugin in plugins]
        
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class _TestPlugin(object):
    def __init__(self, a, b=2):
        self.a = a
        self.b = b

class _TestPlugin2(object):
    pass

class TestPlugin(amcattest.PolicyTestCase):

    def test_get_plugin(self):
        """Can we get a plugin object from the db?"""
        
        s = Plugin.objects.create(module='amcat.models.plugin',
                                  class_name='_TestPlugin')
        self.assertEqual(s.get_class(), _TestPlugin)
        self.assertRaises(TypeError, s.get_instance) # argument a missing
        self.assertEqual(s.get_instance(a=999).a, 999)      # argument via options

        s.arguments = dict(a=123, b="bla")
        s.save()
        s = Plugin.objects.get(pk=s.id)
        
        self.assertEqual(s.get_instance().a, 123) 
        self.assertEqual(s.get_instance().b, "bla")
        self.assertEqual(s.get_instance(b=dict(x={1,2,3})).b, {'x' : {1,2,3}})
        
    def test_plugins_by_type(self):
        s1 = Plugin.objects.create(module='amcat.models.plugin', class_name='_TestPlugin')
        s2 = Plugin.objects.create(module='amcat.models.plugin', class_name='_TestPlugin', type='a')
        s3 = Plugin.objects.create(module='amcat.models.plugin', class_name='_TestPlugin', type='a')
        s4 = Plugin.objects.create(module='amcat.models.plugin', class_name='_TestPlugin2', type='b')

        self.assertEqual([x.__class__ for x in plugins_by_type('b')], [_TestPlugin2])
        self.assertRaises(TypeError, plugins_by_type, 'a') # argument a missing 
        self.assertEqual([x.__class__ for x in plugins_by_type('a', a=1)], [_TestPlugin, _TestPlugin])

        s4.active = False
        s4.save()
        self.assertEqual([x.__class__ for x in plugins_by_type('b')], [])
        
