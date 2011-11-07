from amcat.tools import toolkit

from amcat.tools.idlabel import IDLabel

from amcat.model.ontology.codebook import Codebook
from amcat.model.ontology.code import Code

import logging; log = logging.getLogger(__name__)

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

        @return: a type object such as IDLabel or ont.Code"""
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
        return Code(self.db, value)
    def getTargetType(self):
        return Code
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
