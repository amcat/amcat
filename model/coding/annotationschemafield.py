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
Model module containing AnnotationSchemaField and -Type.

AnnotationSchemaFields are the concrete fields in an AnnotationSchema, e.g.
the subject field in a net coding schema.

AnnotationSchemaFieldTypes are the types of field, e.g. both subject and object
are ontology coding types.
"""

from amcat.tools.model import AmcatModel

from amcat.model.coding.codebook import Codebook

from amcat.model.coding.annotationschema import AnnotationSchema, RequiredValueError

from . import serialiser

from django.db import models

import logging; log = logging.getLogger(__name__)

class AnnotationSchemaFieldType(AmcatModel):
    """
    Model for annotationschemas_fieldtypes

    Field Types are the types of fields available for annotation schemas. They determine
    how values are (de)serialised and which options are available. Most functionality
    is handled by instantiating a Serialiser object using the SerialiserClass column and
    the concrete AnnotationSchemaField from which the serialiser can get details.

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
        db_table = 'annotationschemas_fieldtypes'
        app_label = 'amcat'
        
class AnnotationSchemaField(AmcatModel):
    """Model for annotationschemas_fields

    Fields are the concrete fields in an annotation schema. Every value in an actual
    annotation is bound to an annotation schema field, which can e.g. (de)serialise
    and validate the coded values.
    """
    
    id = models.AutoField(primary_key=True, db_column="annotationschemafield_id")

    annotationschema = models.ForeignKey(AnnotationSchema, related_name='fields')
    fieldnr = models.IntegerField()
    
    fieldname = models.CharField(max_length=20, blank=False, null=False)
    label = models.CharField(max_length=30)
    required = models.BooleanField()
    default = models.BooleanField(db_column='deflt')
    fieldtype = models.ForeignKey(AnnotationSchemaFieldType)
    
    
    #table = models.CharField(max_length=40)
    #keycolumn = models.CharField(max_length=40)
    #labelcolumn = models.CharField(max_length=40)
    #values = models.TextField()
    codebook = models.ForeignKey(Codebook, null=True)

    class Meta():
        db_table = 'annotationschemas_fields'
        app_label = 'amcat'
        unique_together = ("annotationschema", "fieldnr")

    def __unicode__(self):
        return self.fieldname
    
    @property
    def serialiser(self):
        """Get the serialiser for this field"""
        return self.fieldtype.serialiserclass(self)

    def validate(self, value):
        """Validate the given value for this field"""
        if (value is None) and self.required:
            raise RequiredValueError(self)

    def possible_values(self):
        """Get the possible values

        @return: a sequence of (deserialised) values
                 or None if the field is not a 'drop down'
        """
        raise NotImplementedError()

    def value_description(self, value):
        """Get a description for the given (desrialised) value"""
        raise NotImplementedError()

    
    def value_label(self, value):
        """Get a description for the given (deserialised) value"""
        raise NotImplementedError()
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest
        
class TestAnnotationSchemaFieldType(amcattest.PolicyTestCase):
    def test_get_serialiser(self):
        """Are the built in field types present and bound to the right class?"""
        fieldtype = AnnotationSchemaFieldType.objects.get(pk=1)
        self.assertEqual(fieldtype.serialiserclass, serialiser.TextSerialiser)

class TestAnnotationSchemaField(amcattest.PolicyTestCase):
    def test_create_field(self):
        """Can we create a schema field object on a schema"""
        fieldtype = AnnotationSchemaFieldType.objects.get(pk=1)
        a = amcattest.create_test_schema()
        f = AnnotationSchemaField.objects.create(annotationschema=a, fieldnr=1, fieldtype=fieldtype)
        self.assertIsNotNone(f)
        
    def test_values(self):
        """test the possible_values and describe_value functions"""
        fieldtype = AnnotationSchemaFieldType.objects.get(pk=1) # 
        a = amcattest.create_test_schema()
        f = AnnotationSchemaField.objects.create(annotationschema=a, fieldnr=1, fieldtype=fieldtype)
        v = f.possible_values()
        self.assertIsNone(v) # for pk 1

        fieldtype = AnnotationSchemaFieldType.objects.get(pk=3) # lookup field
        f = AnnotationSchemaField.objects.create(annotationschema=a, fieldnr=1, fieldtype=fieldtype)
        v = f.possible_values()
        self.assertTrue(v) # lookup should have values!
        # test possible values
        for val in v:
            f.describe_value(val)
        
        
        
        
