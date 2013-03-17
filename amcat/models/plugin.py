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

"""ORM Module representing plugins"""

from django.db import models
from amcat.tools.model import AmcatModel
from amcat.tools import classtools
from amcat.tools.djangotoolkit import JsonField

class PluginType(AmcatModel):
    """
    Plugin Types list the types of plugins that are available. In general,
    Plugins are user controlled, and Plugin Types are fixed.
    """
    id = models.AutoField(primary_key=True, db_column="plugintype_id")
    label = models.CharField(max_length=100, unique=True)
    class_name = models.CharField(max_length=100, unique=True)

    def get_classes(self):
        return (p.get_class() for p in self.plugins.all())

    def get_class(self):
        """Return the base class defined by this plugin type"""
        return classtools.import_attribute(self.class_name)

    @property
    def description(self):
        return self.get_class().__doc__
    
    class Meta():
        app_label = 'amcat'
        db_table = 'plugintypes'
        
class Plugin(AmcatModel):
    """A Plugin is a piece of code that provide a specific function that can
    be added 'at runtime'"""

    id = models.AutoField(primary_key=True, db_column="plugin_id")
    
    label = models.CharField(max_length=100, unique=True)
    class_name = models.CharField(max_length=100, unique=True)
    plugin_type = models.ForeignKey(PluginType, null=True, related_name='plugins')

    class Meta():
        app_label = 'amcat'
        db_table = 'plugins'

    def get_class(self):
        """Return the class defined by this plugin"""
        return classtools.import_attribute(self.class_name)

    def save(self, *args, **kargs):
        if self.class_name and not self.label:
            self.label = self.class_name.split(".")[-1]
        super(Plugin, self).save(*args, **kargs)
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest


class TestPlugin(amcattest.PolicyTestCase):
    
    def test_get_classes(self):
        pt = PluginType.objects.create(class_name="amcat.models.Article")
        p1 = Plugin.objects.create(class_name="amcat.models.ArticleSet", plugin_type=pt)
        p2 = Plugin.objects.create(class_name="amcat.models.Project", plugin_type=pt)

        from amcat.models import ArticleSet, Project
        self.assertEqual(set(pt.get_classes()), {ArticleSet, Project})

