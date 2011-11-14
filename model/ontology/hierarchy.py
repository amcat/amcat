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

"""
Model module representing ontology Hierarchies
"""

from __future__ import unicode_literals, print_function, absolute_import

from django.db import models

from amcat.tools.model import AmcatModel
from amcat.model.object import Object

import logging; log = logging.getLogger(__name__)

class Hiearchy(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='object_id')

    child = models.ForiegnKey(Object, db_index=True)
    parent = models.ForiegnKey(Object, db_index=True, null=True)
    
    
    # functions = ForeignKey(Function) # TODO: create reverse in Function f

    class Meta():
        db_table = 'hierarchies'
        app_label = 'amcat'


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestHierarchy(amcattest.PolicyTestCase):
    def test_label(self):
        """Can we create objects and assign labels?"""
        o = Object.objects.create()
        l = Language.objects.create()
        l2 = Language.objects.create()
        Label.objects.create(object=o, language=l, label="bla")
        self.assertEqual(o.getLabel(l), "bla")
        self.assertEqual(o.getLabel(l2), "bla", "Object.getLabel fallback does not work")
        Label.objects.create(object=o, language=l2, label="blx")
        self.assertEqual(o.getLabel(l2), "blx")
        self.assertEqual(o.getLabel(Language.objects.create()), "bla")

        self.assertEqual(o.label, "bla")
