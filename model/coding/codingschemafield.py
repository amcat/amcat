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
Model module containing CodingSchemaField and -Type.

CodingSchemaFields are the concrete fields in an CodingSchema, e.g.
the subject field in a net coding schema.

CodingSchemaFieldTypes are the types of field, e.g. both subject and object
are ontology coding types.
"""

from amcat.tools.model import AmcatModel

from amcat.model.coding.codebook import Codebook

from amcat.model.coding.codingschema import CodingSchema, RequiredValueError

from . import serialiser

from django.db import models

import logging; log = logging.getLogger(__name__)

class CodingSchemaFieldType(AmcatModel):
    """
    Model for codingschemas_fieldtypes

    Field Types are the types of fields available for coding schemas. They determine
    how values are (de)serialised and which options are available. Most functionality
    is handled by instantiating a Serialiser object using the SerialiserClass column and
    the concrete CodingSchemaField from which the serialiser can get details.

    For example, a dropdown field is always numeric of type, but the available options are
    determined by parameters in the schema field definition.
    """
    
    id = models.IntegerField(primary_key=True, db_column="fieldtype_id")
    name = models.CharField(max_length=50)
    serialiserclassname = models.CharField(max_length=50, db_column="serialiserclass")

    def __unicode__(self):
        return self.name

    @property
    def serialiserclass(self):
        """Get the serialiser class for this field type"""
        return getattr(serialiser, self.serialiserclassname)

    def create_serialiser(self, field):
        """Create a serialiser object for this field type with the given field"""
        pass

    
    class Meta():
        db_table = 'codingschemas_fieldtypes'
        app_label = 'amcat'
        
class CodingSchemaField(AmcatModel):
    """Model for codingschemas_fields

    Fields are the concrete fields in an coding schema. Every value in an actual
    coding is bound to an coding schema field, which can e.g. (de)serialise
    and validate the coded values.
    """
    
    id = models.AutoField(primary_key=True, db_column="codingschemafield_id")

    codingschema = models.ForeignKey(CodingSchema, related_name='fields')
    fieldnr = models.IntegerField(default=0)
    
    label = models.TextField()
    required = models.BooleanField(default=True)
    default = models.CharField(db_column='deflt', max_length=50, null=True)
    fieldtype = models.ForeignKey(CodingSchemaFieldType)
    
    codebook = models.ForeignKey(Codebook, null=True) # for codebook fields

    class Meta():
        db_table = 'codingschemas_fields'
        app_label = 'amcat'

    def __unicode__(self):
        return self.label

    @property
    def serialiser(self):
        """Get the serialiser for this field"""
        return self.fieldtype.serialiserclass(self)

    def validate(self, value):
        """Validate the given value for this field"""
        if (value is None) and self.required:
            raise RequiredValueError(self)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest
        
class TestCodingSchemaFieldType(amcattest.PolicyTestCase):
    def test_get_serialiser(self):
        """Are the built in field types present and bound to the right class?"""
        fieldtype = CodingSchemaFieldType.objects.get(pk=1)
        self.assertEqual(fieldtype.serialiserclass, serialiser.TextSerialiser)

class TestCodingSchemaField(amcattest.PolicyTestCase):
    def test_create_field(self):
        """Can we create a schema field object on a schema"""
        fieldtype = CodingSchemaFieldType.objects.get(pk=1)
        a = amcattest.create_test_schema()
        f = CodingSchemaField.objects.create(codingschema=a, fieldnr=1, fieldtype=fieldtype)
        self.assertIsNotNone(f)
        
        
        
        
