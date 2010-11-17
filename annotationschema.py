import toolkit, project, ont, article, dbtoolkit, sentence
from cachable2 import Cachable, DBProperty, ForeignKey, DBProperties
import cachable
from table3 import ObjectColumn
from idlabel import IDLabel

def paramdict(paramstr):
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
    
    
    def createField(self, fieldnr, fieldname, label, fieldtype, params, deflt):
        if fieldtype in (5,):
            return OntologyAnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
        elif fieldtype in (3,4,8):
            return LookupAnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
        elif fieldtype == 12:
            return FromAnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
        else:
            return AnnotationSchemaField(self, fieldnr, fieldname, label, fieldtype, params, deflt)
    

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

        
class AnnotationSchemaField(Cachable):
    __table__ = 'annotationschemas_fields'
    __idcolumn__ = ('annotationschemaid','fieldnr')

    schema = DBProperty(AnnotationSchema, getcolumn="annotationschemaid")
    fieldname, label, default = DBProperties(3)
    params = DBProperty(paramdict)
    fieldtype = DBProperty()
    
    def deserialize(self, value):
        return value
    def getLabel(self, value, annotation=None):
        if type(value) == float:
            return "%1.2f"  % value
        return value
    def getValue(self, unit):
        return unit.getValue(self)
    def hasLabel(self):
        return False
    def cache(self):
        pass

class LookupAnnotationSchemaField(AnnotationSchemaField):
    def __init__(self, *vals):
        AnnotationSchemaField.__init__(self, *vals)
        self._labels = None
    def deserialize(self, value):
        if value is None: return None
        label = self.getLabels().get(value, None)
        result = IDLabel(value, label)
        return result
        # raise Exception([value, self.getLabels().get(value, None), self.getLabels()])
        #return LookupValue(value, self.getLabels().get(value, None))
    def hasLabel(self):
        return True
    def getLabels(self):
        if self._labels is None:
            if self.fieldtype == 4:
                self._labels = {}
                for i, val in enumerate(self.params['values'].split(";")):
                    if ":" in val:
                        i, val = val.split(":")
                        i = int(i)
                    self._labels[i] = val
            else:
                sql = "SELECT %s, %s FROM %s" % (self.params['key'], self.params['label'], self.params['table'])
                
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
                
                result = self.schema.db.doQuery(sql)
                self._labels = dict((k,v.decode('latin-1')) for k,v in result)
                #self._labels = {}
                #for i in xrange(len(result)):
                #    self._labels[i] = result[i][1]
                
        return self._labels
    def getLabel(self, value, annotation=None):
        if value is None: return None
        if type(value) in (int, float, str, unicode):
            return str(value)
        return value.label
        #v = self.deserialize(value)
        #if not v: return None
        #return "@@ %r / %r / %r / %r $$" % (value, v, v.id, v.label)
        #return v.label
    def cache(self):
        self.getLabels()
        
        
class LookupValue(IDLabel):
    pass

class FromAnnotationSchemaField(AnnotationSchemaField):
    def __init__(self, *vals):
        AnnotationSchemaField.__init__(self, *vals)
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

    def hasLabel(self):
        return True
        
        
class OntologyAnnotationSchemaField(AnnotationSchemaField):
    def __init__(self, *vals):
        AnnotationSchemaField.__init__(self, *vals)
        self._set = None
    def deserialize(self, value):
        if value is None: return None
        return ont.Object(self.schema.db, value, languageid=self.schema.language)
    @property
    def set(self):
        if self._set is None:
            setid = self.params.get("setid")
            if not setid: setid = self.params.get("set")
            if not setid: setid = self.params.get("sets")
            if not setid:
                toolkit.warn("OntologyASF without setid? %s" % (self.params))
                return None
            self._set = ont.Set(self.schema.db, int(setid))
        return self._set
    def getLabel(self, value, codedsentence=None):
        v = self.deserialize(value)
       
        if not v: return None
        try:
            return v.getLabel()
        except AttributeError:
            return v
    def hasLabel(self):
        return True
    def cache(self):
        if self.set:
            self.set.cacheLabels()
            
def getFieldType(field):
    if type(field) in (OntologyAnnotationSchemaField, LookupAnnotationSchemaField):
        return IDLabel
    elif field.fieldtype in (6,9):
        return float
    elif field.fieldtype in (2,):
        return int
    return str

def getValue(unit, field):
    if unit is None: return None
    return unit.getValue(field.fieldname)

class FieldColumn(ObjectColumn):
    """ObjectColumn based on a AnnotationSchemaField"""
    def __init__(self, field, article):
        ObjectColumn.__init__(self, field.label, fieldname=field.fieldname, fieldtype=getFieldType(field))
        self.field = field
        self.article = article
        self.valuelabels = {}
    def getUnit(self, row):
        return row.ca if self.article else row.cs
    def getCell(self, row):
        val = getValue(self.getUnit(row), self.field)
        
        return val
