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
Model module containing AnnotationSchema, representing a annotation or coding
schema to be used for manual coding
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools.model import AmcatModel
from amcat.model.project import Project

from django.db import models

import logging; log = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Error in validating a field"""
    pass

class RequiredValueError(ValidationError):
    """Validation Error used when a required field is missing"""
    pass

class AnnotationSchema(AmcatModel):
    """Model for table annotationschemas: A coding schema used for manual coding"""
    id = models.AutoField(db_column='annotationschema_id', primary_key=True)

    name = models.CharField(max_length=75)
    description = models.TextField()

    isnet = models.BooleanField()
    isarticleschema = models.BooleanField()
    quasisentences = models.BooleanField()

    project = models.ForeignKey(Project)
    
    def __unicode__(self):
        return "%s - %s" % (self.id, self.name)

    class Meta():
        db_table = 'annotationschemas'
        app_label = 'amcat'

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestAnnotationSchema(amcattest.PolicyTestCase):
    def test_create(self):
        """Test whether annotation schema objects can be created"""
        s = amcattest.create_test_schema(name='test')
        self.assertEqual(s.name, 'test')
