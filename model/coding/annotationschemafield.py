from amcat.tools import toolkit

from amcat.tools.table.table3 import ObjectColumn
from amcat.tools.idlabel import IDLabel
from amcat.tools.model import AmcatModel

from amcat.model.ontology.codebook import Codebook
from amcat.model.ontology.code import Code

from amcat.model.project import Project

from django.db import models

import logging; log = logging.getLogger(__name__)

class AnnotationSchemaFieldType(AmcatModel):
    id = models.IntegerField(primary_key=True, db_column="fieldtype_id")
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    class Meta():
        db_table = 'annotationschemas_fieldtypes'
        app_label = 'coding'
        
class AnnotationSchemaField(AmcatModel):    
    annotationschema = models.ForeignKey(AnnotationSchema)

    fieldname = models.CharField(max_length=20)
    label = models.CharField(max_length=30)
    required = models.BooleanField()
    default = models.BooleanField(db_column='deflt')

    fieldtype = models.ForeignKey(AnnotationSchemaFieldType)

    table = models.CharField(max_length=40)
    keycolumn = models.CharField(max_length=40)
    labelcolumn = models.CharField(max_length=40)
    values = models.TextField()

    codebook = models.ForeignKey(Codebook)

    class Meta():
        db_table = 'annotationschemas_fields'
        app_label = 'coding'
        unique_together = ("annotationschema", "fieldnr")

    @property
    def serializer(self):
        try:
            return self._serializer
        except AttributeError:
            pass
        
        ftid = self.fieldtype.id
        if ftid == 5:
            codebookid = self.codebook.id if self.codebook else 201
            self._serializer = OntologyFieldSerialiser(self.schema.db, codebookid)
        elif ftid == 4:
            self._serializer = AdHocLookupFieldSerialiser(self.values)
        elif ftid in (3,8):
            self._serializer = DBLookupFieldSerialiser(self.schema.db, self.table, self.keycolumn, self.labelcolumn)
        elif ftid == 12:
            self._serializer = FromFieldSerialiser()
        else:
            if ftid == 2: ftype = int
            elif ftid in (6,9): ftype = float
            elif ftid == 7: ftype = int #treat bool as int since spsss doe not have bool type
            else: ftype = str
            self._serializer = SchemaFieldSerialiser(ftype)
            
        return self._serializer

    def deserialize(self, value):
        val = self.serializer.deserialize(value)
        log.debug("%r/%r deserialised %r to %r" % (self, self.serializer, value, val))
        return val

    def getTargetType(self):
        return self.serializer.getTargetType()   

    def validate(self, value):
        if (value is None) and self.required:
            raise RequiredValueError(self)
