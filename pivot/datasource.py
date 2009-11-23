"""
Module containting the interface definitions and base implementations
of the DataSource and related objects

Interface Field
  datasource : DataSource
  concept : Concept

Interface Mapping
  a. b : Field
  geCost(bool reverse=False) : float
  map(a', bool reverse=False) : 0..n b'   # a' = object corresponding to concept a
 
Interface DataSource
  getMappings yields* mappings
  
Interface DataModel
  register(datasource) 
  getConcepts()
  getRoute(*concepts) yields* mappings
  
*) yields Xs = return something that is an iterator/generator/collection etc of X


# txt = open("file.txt").read().decode("utf-8") 
"""

import collections
from toolkit import Identity

################### Base implementations ##############################

class Field(Identity):
    def __init__(self, datasource, concept):
        Identity.__init__(self, datasource, concept)
        self.datasource = datasource
        self.concept = concept
    def __repr__(self):
        return 'Field(%s, %s)' % (self.datasource, self.concept)
    def __str__(self):
        return '%s::%s' % (self.datasource, self.concept)

        
class Mapping(Identity):
    def __init__(self, a, b, cost=1.0, reversecost=10.0):
        Identity.__init__(self, a, b)
        self.a = a
        self.b = b
        self._cost = cost
        self._reversecost = reversecost
    def getCost(self, reverse=False):
        return self._reversecost if reverse else self._cost
    def map(self, value, reverse=False):
        abstract
    def getNodes(self):
        "to implement IEdge"
        return [self.a, self.b]
    
class DataSource(object):
    def __init__(self, mappings = None):
        self._mappings = mappings or set()
    def getMappings(self):
        return self._mappings
        
class FieldConceptMapping(Mapping):
    def __init__(self, concept, field):
        Mapping.__init__(self, concept, field, 1.0, 1.0)
    def map(self, value, reverse="dummy"):
        return [value]        

class DataModel(object):
    def __init__(self, datasources = None):
        self._datasources = datasources or set()
    def register(self, datasource):
        self._datasources.add(datasource)
    def getConcepts(self):
        c = set()
        for ds in self._datasources:
            for m in ds.getMappings(): 
                c.add(m.a.concept)
                c.add(m.b.concept)
        return c   
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
                yield FieldConceptMapping(concept, field)
        
################### Simple implementations ##############################

class FunctionalMapping(Mapping):
    def __init__(self, a, b, mapfunc, reversefunc):
        Mapping.__init__(self, a, b)
        self._mapfunc = mapfunc
        self._reversefunc = reversefunc
    def map(self, a, reverse=False):
        f = self._reversefunc if reverse else self._mapfunc
        return f(a)
    
class FunctionalDataModel(DataModel):
    def __init__(self, solverfunc):
        DataModel.__init__(self)
        self._solverfunc = solverfunc
    def getRoute(self, *concepts):
        mappings= set()
        for datasource in self._datasources:
            mappings |= set(datasource.getMappings())
        mappings |= set(self.getFieldConceptMappings())
        return self._solverfunc(mappings, concepts)
