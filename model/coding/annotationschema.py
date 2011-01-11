from amcat.tools import toolkit
from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.tools.cachable import cacher
from amcat.tools.table.table3 import ObjectColumn
from amcat.tools.idlabel import IDLabel

from amcat.model.ontology.codebook import Codebook
from amcat.model.ontology.object import Object

import logging; log = logging.getLogger(__name__)
#import amcatlogging; amcatlogging.debugModule()


class AnnotationSchema(Cachable):
    __idcolumn__ = 'annotationschemaid'
    __table__ = 'annotationschemas'
    __labelprop__ = 'name'
    
    name, isarticleschema, location = DBProperties(3)
    fields = ForeignKey(lambda:AnnotationSchemaField)
    
    @property
    def table(self):
        return self.location.split(":")[0]
    
    
    def getField(self, fieldname):
        for f in self.fields:
            if f.fieldname == fieldname: return f

    def SQLSelect(self, extra = []):
        fields = extra + [f.fieldname for f in self.fields]
        return "select [%s] from %s " % ("],[".join(fields), self.table)

    def asDict(self, values):
        return dict(zip([f.fieldname for f in self.fields], values))

    def fieldNames(self):
        return (f.fieldname for f in self.fields)

    def cacheMany(self, units):
        cachable.cache(units, *self.fieldNames())
    
    def idname(self):
        return "%i - %s" % (self.id, self.name)

    def __hash__(self):
        return hash(self.id)
    def __eq__(self, other):
        return type(other) == AnnotationSchema and other.id == self.id

def getAnnotationschemas(db):
    """ Iterate over all annotation schema objects """
    ids = db.doQuery("SELECT annotationschemaid FROM annotationschemas")
    for a in ids:
        yield AnnotationSchema(db, a[0])


class AnnotationSchemaFieldType(Cachable):
    __table__ = "annotationschemas_fieldtypes"
    __idcolumn__ = "fieldtypeid"
    __labelprop__ = "name"
    name = DBProperty()
        
class AnnotationSchemaField(Cachable):
    __table__ = 'annotationschemas_fields'
    __idcolumn__ = ('annotationschemaid','fieldnr')

    schema = DBProperty(AnnotationSchema, getcolumn="annotationschemaid")
    fieldname, label, default = DBProperties(3)
    fieldtype = DBProperty(AnnotationSchemaFieldType)

    table, keycolumn, labelcolumn, values = DBProperties(4)
    codebook = DBProperty(Codebook)

    @property
    def serializer(self):
        try:
            return self._serializer
        except AttributeError: pass
        
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
        log.debug("%s/%s deserialised %r to %r" % (self, self.serializer, value, val))
        return val
    def getTargetType(self):
        return self.serializer.getTargetType()   
    


class SchemaFieldSerialiser(object):
    """Base class for serialisation support for schema fields"""
    def __init__(self, targettype):
        self.targettype = targettype
    def deserialize(self, value):
        """Convert the given (db) value to a domain object"""
        return value
    def getTargetType(self):
        """Return the type of objects dererialisation will yield

        @return: a type object such as IDLabel or ont.Object"""
        return self.targettype
    
class LookupFieldSerialiser(SchemaFieldSerialiser):
    def deserialize(self, value):
        if value is None: return None
        label = self.getLabels().get(value, None)
        result = IDLabel(value, label)
        return result
    def getTargetType(self):
        return IDLabel
    
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
        
        # BUG (see part of e-mail below).
        # 
        # [ e-mail]
        # ..certain countries/organizations (I suspect those that were added or changed
        # by the Swiss team) are still represented with an ID number instead of their name.
        # When the coders e.g. coded "NATO", AmCAT shows "IDLabel(282)".
        #
        # To a similar extent, for the variables "actor1-3", "mp1-3", and "canton1-3",
        # AmCAT only rarely shows labels. Most of the annotations appear in the form "IDLabel(63)"
        # (standing here for what the coder wanted to be "206 Delamuraz Jean-Pascal").
        # [/ e-mail ]
        #
        # This is probably causes by iNet, which doesn't select id fields (206) but a row
        # number (63).
        
        result = self.db.select(self.table, [self.keycol, self.labelcol])
        self._labels = dict((k,v.decode('latin-1')) for k,v in result)
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


def getValue(unit, field):
    if unit is None: return None
    return unit.getValue(field.fieldname)

class FieldColumn(ObjectColumn):
    """ObjectColumn based on a AnnotationSchemaField"""
    def __init__(self, field, article, fieldname=None, label=None):
        if fieldname is None: fieldname = field.fieldname
        if label is None: label = field.label
        ObjectColumn.__init__(self, label, fieldname, fieldtype=field.getTargetType())
        self.field = field
        self.article = article
        self.valuelabels = {}
    def getUnit(self, row):
        return row.ca if self.article else row.cs
    def getCell(self, row):
        try:
	    unit = self.getUnit(row)
            val = getValue(unit, self.field)
            return val
        except AttributeError, e:
            log.debug("AttributeError on getting %s.%s: %s" % (row, self.field, e))
            return None
            
                     

if __name__ == '__main__':
    import amcatlogging; amcatlogging.setup()
    import dbtoolkit, ont
    db = dbtoolkit.amcatDB()
    a = AnnotationSchema(db, 72)
    obj = ont.Object(db, 11344)
    f = a.getField("subject")
    s = f.serializer.set
    print s.categorise(obj, date=None, depth=[1], returnOmklap=True, returnObjects=True)

    
