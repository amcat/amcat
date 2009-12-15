"""
Module containting the interface definitions and base implementations
of the DataSource and related objects

Interface Field
  datasource : DataSource
  concept : Concept
  getConceptMapping : Mapping

Interface Mapping
  a, b : Field
  geCost(bool reverse=False) : float
  map(a', bool reverse=False) : sequence of b'   # a' = object corresponding to concept a
 
Interface DataSource
  getMappings : sequence of Mapping
  
Interface DataModel
  register(datasource) 
  getConcepts() : Concept
  getMappings(): sequence of Mapping

Interface Concept:
  pass (opaque)
"""

import collections
from toolkit import Identity, IDLabel
import project
################### Base implementations ##############################

class Field(Identity):
    def __init__(self, datasource, concept):
        Identity.__init__(self, datasource, concept)
        self.datasource = datasource
        self.concept = concept
    def getConceptMapping(self):
        return FieldConceptMapping(self.concept, self)
    def __str__(self):
        return '%s::%s' % (self.datasource, self.concept)
    __repr__ = __str__

        
class Mapping(Identity):
    def __init__(self, a, b, cost=1.0, reversecost=10.0):
        Identity.__init__(self, a, b)
        self.a = a
        self.b = b
        self._cost = cost
        self._reversecost = reversecost
    def getCost(self, reverse=False):
        return self._reversecost if reverse else self._cost
    def map(self, value, reverse=False, memo=None):
        abstract
    def startMapping(self, values, reverse=False):
        """
        Allows a mapping to prepare the mapping of the given values and
        return a 'memo' object that will be passed on to the map call
        """
        pass
    def __str__(self):
        return "%s -> %s" % (self.a, self.b)
    __repr__ = __str__
    
    
class DataSource(object):
    def __init__(self, mappings = None):
        self._mappings = mappings or set()
    def getMappings(self):
        return self._mappings
        
class FieldConceptMapping(Mapping):
    def __init__(self, concept, field, func=None):
        Mapping.__init__(self, concept, field, 1.0, 1.0)
        self.func = func
    def map(self, value, reverse=False, memo=None):
        if self.func:
            return [self.func(value, reverse)]
        else:
            return [value]
    def __str__(self):
        return "%s => %s" % (self.a, self.b)
    __repr__ = __str__

conceptmap = {
    "project" : project.Project,
    "batch" : project.Batch,
    "source" : lambda db, id: db.sources.lookupID(id),
    }

class Concept(object):
    def __init__(self, datamodel, label):
        self.datamodel = datamodel
        self.label = label
    def getObject(self, db, id):
        if self.label in conceptmap:
            return conceptmap[self.label](db, id)
        return id
    def __str__(self):
        return self.label
    def __repr__(self):
        return "Concept(%s)" % self.label
    
class DataModel(object):
    def __init__(self, datasources = None):
        self._datasources = datasources or set()
        self._concepts = {} # identifier -> concept
    def register(self, datasource):
        self._datasources.add(datasource)
    def getConcept(self, identifier):
        if identifier not in self._concepts:
            self._concepts[identifier] = Concept(self, identifier)
        return self._concepts[identifier] 
    def getConcepts(self):
        return self._concepts.values()
    def getRoute(self):
        abstract
    def getFieldConceptMappings(self):
        fieldmap = collections.defaultdict(set) # concept : 1..n field
        for datasource in self._datasources:
            for mapping in datasource.getMappings():
                for field in mapping.a, mapping.b:
                    fieldmap[field.concept].add(field)
        for concept, fields in fieldmap.items():
            for field in fields:
                yield field.getConceptMapping()
            
                
    def getMappings(self):
        for datasource in self._datasources:
            for mapping in datasource.getMappings():
                yield mapping
        for mapping in self.getFieldConceptMappings():
            yield mapping
        
        
################### Simple implementations ##############################

class FunctionalMapping(Mapping):
    def __init__(self, a, b, mapfunc, reversefunc):
        Mapping.__init__(self, a, b)
        self._mapfunc = mapfunc
        self._reversefunc = reversefunc
    def map(self, a, reverse=False, memo=None):
        f = self._reversefunc if reverse else self._mapfunc
        return f(a)
