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
Model module containing CodingSchema, representing a coding or coding
schema to be used for manual coding
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools.model import AmcatModel

from django.db import models

import logging; log = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Error in validating a field"""
    pass

class RequiredValueError(ValidationError):
    """Validation Error used when a required field is missing"""
    pass

class CodingSchema(AmcatModel):
    """Model for table codingschemas: A coding schema used for manual coding"""
    id = models.AutoField(db_column='codingschema_id', primary_key=True)
    __label__ = 'name'
    
    name = models.CharField(max_length=75)
    description = models.TextField(null=True)

    isarticleschema = models.BooleanField(default=False)
    subsentences = models.BooleanField(default=False, help_text="Allow subsentences to be coded.")

    project = models.ForeignKey("amcat.Project")
    highlighters = models.ManyToManyField("amcat.Codebook")
    highlight_language = models.ForeignKey("amcat.Language", null=True)

    def __unicode__(self):
        return "%s - %s" % (self.id, self.name)

    class Meta():
        ordering = ['name']
        db_table = 'codingschemas'
        app_label = 'amcat'

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodingSchema(amcattest.AmCATTestCase):
    def test_create(self):
        """Test whether coding schema objects can be created"""
        s = amcattest.create_test_schema(name='test')
        self.assertEqual(s.name, 'test')
