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
the subject field in a net codingschema.

CodingSchemaFieldTypes are the types of field, e.g. both subject and object
are ontology coding types.
"""
import logging

from amcat.tools.model import AmcatModel
from amcat.models.coding.codebook import Codebook
from amcat.models.coding.codingschema import CodingSchema, RequiredValueError
from amcat.models.coding import serialiser

from django.db import models


log = logging.getLogger(__name__)


class FIELDTYPE_IDS:
    TEXT = 1
    INT = 2
    CODEBOOK = 5
    BOOLEAN = 7
    QUALITY = 9


class CodingSchemaFieldType(AmcatModel):
    """
    Model for codingschemas_fieldtypes

    Field Types are the types of fields available for codingschemas. They determine
    how values are (de)serialised and which options are available. Most functionality
    is handled by instantiating a Serialiser object using the SerialiserClass column and
    the concrete CodingSchemaField from which the serialiser can get details.

    For example, a dropdown field is always numeric of type, but the available options are
    determined by parameters in the schema field definition.
    """
    __label__ = 'name'
    
    id = models.IntegerField(primary_key=True, db_column="fieldtype_id")
    name = models.CharField(max_length=50, unique=True)
    serialiserclassname = models.CharField(max_length=50, db_column="serialiserclass")

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

    Fields are the concrete fields in an codingschema. Every value in an actual
    coding is bound to an codingschema field, which can e.g. (de)serialise
    and validate the coded values.
    """
    
    id = models.AutoField(primary_key=True, db_column="codingschemafield_id")

    codingschema = models.ForeignKey(CodingSchema, related_name='fields')
    fieldnr = models.IntegerField(default=0)
    
    label = models.TextField()
    required = models.BooleanField(default=True)
    fieldtype = models.ForeignKey(CodingSchemaFieldType)
    
    codebook = models.ForeignKey(Codebook, null=True) # for codebook fields
    split_codebook = models.BooleanField(default=False, help_text="Do not display a list of all codes in annotator, " +
                                                                   "but let the user first choose a root and then " + 
                                                                   "one of its descendants.")

    # Default needs to the last field specified, in order to allow checks on
    # `fieldtype` when validating `default` in forms.
    default = models.CharField(db_column='deflt', max_length=50, null=True, blank=True)

    class Meta():
        db_table = 'codingschemas_fields'
        app_label = 'amcat'

    @property
    def serialiser(self):
        """Get the serialiser for this field"""
        return self.fieldtype.serialiserclass(self)

    def validate(self, value):
        """Validate the given value for this field"""
        if (value is None) and self.required:
            raise RequiredValueError(self)
