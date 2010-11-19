import toolkit, project, ont, article, dbtoolkit, sentence
from cachable2 import Cachable, DBProperty, ForeignKey, DBProperties
import cachable
from table3 import ObjectColumn
from idlabel import IDLabel
import logging; log = logging.getLogger(__name__)
#import amcatlogging; amcatlogging.debugModule()

def paramdict(db, paramstr):
    d = {}
    if not paramstr: return d
    for kv in paramstr.split(","):
        k,v = kv.split("=")
        d[k.strip()] = v.strip()
    return d

class AnnotationSchema(Cachable):
    __idcolumn__ = 'annotationschemaid'
    __table__ = 'annotationschemas'
    __dbproperties__ = ["name", "articleschema"]
    __labelprop__ = 'name'
    
    name, articleschema, location = DBProperties(3)
    params = DBProperty(paramdict)
    fields = ForeignKey(lambda:AnnotationSchemaField)
    
    @property
    def table(self):
        return self.location.split(":")[0]
    
    
    def getField(self, fieldname):
        for f in self.fields:
            if f.fieldname == fieldname: return f

    @property
    def language(self):
        return int(self.params.get("language", 1))

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
    params = DBProperty(paramdict)
    fieldtype = DBProperty(AnnotationSchemaFieldType)

    @property
    def serializer(self):
        try:
            return self._serializer
        except AttributeError: pass
        
        ftid = self.fieldtype.id
        if ftid == 5:
            setid = self.params.get("setid")
            if not setid: setid = self.params.get("set")
            if not setid: setid = self.params.get("sets")
            if not setid:
                log.warn("OntologyASF without setid? %s" % (self.params))
                self._serializer = SchemaFieldSerialiser()
            self._serializer = OntologyFieldSerialiser(self.schema.db, self.schema.language, int(setid))
        elif ftid == 4:
            self._serializer = AdHocLookupFieldSerialiser(self.params["values"])
        elif ftid in (3,8):
            self._serializer = DBLookupFieldSerialiser(self.schema.db, *map(self.params.get, ["table","key","label"]))
        elif ftid == 12:
            self._serializer = FromFieldSerialiser()
        else:
            self._serializer = SchemaFieldSerialiser()
            
        return self._serializer

    def deserialize(self, value):
        val = self.serializer.deserialize(value)
        log.debug("%s/%s deserialised %r to %r" % (self, self.serializer, value, val))
        return val
    def getTargetType(self):
        return self.serializer.getTargetType()   
    


class SchemaFieldSerialiser(object):
    """Base class for serialisation support for schema fields"""
    def deserialize(self, value):
        """Convert the given (db) value to a domain object"""
        return value
    def getTargetType(self):
        """Return the type of objects dererialisation will yield

        @return: a type object such as IDLabel or ont.Object"""
        return object
    
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
    def __init__(self, db, language, setid):
        self.db = db
        self.language = language
        self.setid = setid
    def deserialize(self, value):
        if value is None: return None
        return ont.Object(self.db, value, languageid=self.language)
    def getTargetType(self):
        return ont.Object
    @property
    def set(self):
        try:
            return self._set
        except AttributeError: pass
        self._set = ont.Set(self.db, self.setid)
        return self._set


def getValue(unit, field):
    if unit is None: return None
    return unit.getValue(field.fieldname)

class FieldColumn(ObjectColumn):
    """ObjectColumn based on a AnnotationSchemaField"""
    def __init__(self, field, article):
        ObjectColumn.__init__(self, field.label, fieldname=field.fieldname, fieldtype=field.getTargetType())
        self.field = field
        self.article = article
        self.valuelabels = {}
    def getUnit(self, row):
        return row.ca if self.article else row.cs
    def getCell(self, row):
        val = getValue(self.getUnit(row), self.field)
        
        return val
