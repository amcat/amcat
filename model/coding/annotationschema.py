from amcat.tools import toolkit

from amcat.tools.table.table3 import ObjectColumn
from amcat.tools.idlabel import IDLabel
from amcat.tools.model import AmcatModel

from amcat.model.ontology.codebook import Codebook
from amcat.model.ontology.object import Object

from django.db import models

import logging; log = logging.getLogger(__name__)

class ValidationError(ValueError):
    pass

class RequiredValueError(ValidationError):
    pass

class AnnotationSchema(AmcatModel):
    id = models.IntegerKey(db_column='annotationschema_id', primary_key=True)

    name = models.CharField(max_length=75)
    description = models.TextField()

    isnet = models.BooleanField()
    isarticleschema = models.BooleanField()
    quasisentences = models.BooleanField()
    
    def __unicode__(self):
        return "%s - %s" % (self.id, self.name)

    class Meta():
        db_table = 'annotationschemas'
        app_label = 'coding'

    def asDict(self, values):
        return dict(zip([f.fieldname for f in self.fields], values))

    def validate(self, values):
        """Validate whether the given values are a valid coding for this schema
        raises a VAlidationError if not, returns silenty if ok.

        @param values: Dict of {schemafield : (deserialized) values}
        """
        for field in self.fields:
            field.validate(values.get(field))

    def deserializeValues(self, **values):
        """Deserialize a {fieldname:valuestr} dict to a {field:value} dict"""
        objects = {}
        for (k,v) in values.items():
            f = self.getField(k)
            o = f.deserialize(v)
            objects[f] = o
        return objects


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

    fieldname = models.Charfield(max_length=20)
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


class SchemaFieldSerialiser(object):
    """Base class for serialisation support for schema fields"""
    def __init__(self, targettype):
        self.targettype = targettype
    def deserialize(self, value):
        """Convert the given (db) value to a domain object"""
        if type(value) == str:
            return value.decode('latin-1') # hack for the mssql db, remove later
        return value
    def serialize(self, value):
        return value
    def getTargetType(self):
        """Return the type of objects dererialisation will yield

        @return: a type object such as IDLabel or ont.Object"""
        return self.targettype
    def getLabels(self):
        """ @return: dict of IDs and labels if the field has one, None otherwise """
        return None
    
class LookupFieldSerialiser(SchemaFieldSerialiser):
    def deserialize(self, value):
        if value is None: return None
        label = self.getLabels().get(value, None)
        result = IDLabel(value, label)
        return result
    def getTargetType(self):
        return IDLabel
    def serialize(self, value):
        if value is None: return
        if type(value) == int: return value
        return value.id
    
class AdHocLookupFieldSerialiser(LookupFieldSerialiser):
    def __init__(self, valuestr):
        self._labels = {}
        for i, val in enumerate(valuestr.split(";")):
            if ":" in val:
                i, val = val.split(":")
                i = int(i)
                self._labels[i] = val
    def getLabels(self):
        return self._labels

class DBLookupFieldSerialiser(LookupFieldSerialiser):
    def __init__(self, db, table, keycol, labelcol):
        if table is None: raise TypeError("DBLookupFieldSerialiser.table should not be None!")
        self.db = db
        self.keycol = keycol
        self.labelcol = labelcol
        self.table = table
    def getLabels(self):
        try:
            return self._labels
        except AttributeError: pass
        
        # TODO
        
        return self._labels
        
        
class FromFieldSerialiser(SchemaFieldSerialiser):
    def __init__(self):
        SchemaFieldSerialiser.__init__(self, int)
    def deserialise(self, value):
        return NotImplementedError()
    def getLabel(self, value, codedsentence=None):
        froms = []
        for s in codedsentence.ca.sentences:
            if s.sentence == codedsentence.sentence:
                val = s.getValue(self.fieldname)
                if not val: val = 0
                froms.append(val)
        froms.sort()
        if not value: value = 0
        i = froms.index(value)
        
        if i == len(froms)-1: to = None
        else: to = froms[i+1]

        return " ".join(codedsentence.sentence.text.split()[value:to])
    def getTargetType(self):
        return IDLabel
        
        
class OntologyFieldSerialiser(SchemaFieldSerialiser):
    def __init__(self, db, codebookid):
        self.db = db
        self.codebookid = codebookid
    def deserialize(self, value):
        if value is None: return None
        return Object(self.db, value)
    def getTargetType(self):
        return Object
    @property
    def codebook(self):
        try:
            return self._set
        except AttributeError: pass
        self._set = Codebook(self.db, self.codebookid)
        return self._set
    def getLabels(self):
        try:
            return self._labels
        except AttributeError: pass

        # TODO: need to support trees as well? now codebookid 5015 has no labels
        self._labels = dict((o.id, unicode(o.label)) for o in self.codebook.objects)
        return self._labels
    def serialize(self, value):
        if value is None: return
        if type(value) == int: return value
        return value.id

class FieldColumn(ObjectColumn):
    """ObjectColumn based on a AnnotationSchemaField"""
    def __init__(self, field, article=None, fieldname=None, label=None, fieldtype=None):
        if fieldtype is None: fieldtype = field.getTargetType()
        if article is None: article = field.schema.isarticleschema
        if fieldname is None: fieldname = field.fieldname
        if label is None: label = field.label
        ObjectColumn.__init__(self, label, fieldname, fieldtype=fieldtype)
        self.field = field
        self.article = article
        self.valuelabels = {}
    def getUnit(self, row):
        return row.ca if self.article else row.cs
    def getCell(self, row):
        try:
            val = self.getValue(row)
            return val
        except AttributeError, e:
            log.debug("AttributeError on getting %s.%s: %s" % (row, self.field, e))
            raise
            return None
    def getValues(self, row):
        unit = self.getUnit(row)
        if unit is None: return None
        values = unit.values
        return values
        
    def getValue(self, row, fieldname = None):
        if not fieldname: fieldname = self.field.fieldname
        log.debug(">>>>>> getValue(%r, %r)" % (row, fieldname))
        values = self.getValues(row)
        if values is None: return None
        try:
            val = getattr(values, fieldname)
        except AttributeError:
            log.error("%r has no field %r, but it has %r" % (values, fieldname, dir(values)))
            raise
        log.debug(">>>>>> values=%r, fieldname=%r, --> val=%s" % (values, fieldname, val))
        return val