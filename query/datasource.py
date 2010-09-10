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
import project, toolkit, article, sources
#import association, amcatxapian, dbtoolkit,article
################### Base implementations ##############################

import datamodel
DataModel = datamodel.DataModel


class Field(Identity):
    """
    Fields represent fields within datasources, ie concrete instantiations of Concepts
    A field has a datasource and concept, and it creates the Mapping from this Concept to itself.
    This mappping allows a conversion between Concept values (e.g. Article objects) and datasource
    specific values (e.g. article ids).
    """
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
    """
    Mappings represent the edges in the data graph and link two Fields or a
    Field and a Concept (see FieldConceptMapping). A mapping has references
    to two Field/Concepts (a and b) and can give the estimated cost for
    traversing it. It can also execute the mapping of concrete values
    """
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
    """ 
    Datasource represents the datasource (e.g. articles, sentiment, associations). 
    A datasource contains mapping(s) of fields to Concepts or other fields.
    """
    def __init__(self, mappings = None):
        if mappings:
            self.setMappings(*mappings)
    def setMappings(self, *mappings):
        self._mappings = mappings or set()
    def getMappings(self):
        return self._mappings
    def deserialize(self, concept, value):
        return None
    def getPossibleValues(self, concept):
        return None

    def __str__(self):
        return "<%s>" % (self.__class__.__name__)
        
class FieldConceptMapping(Mapping):
    """ 
    Maps a Field to a Concept.
    """
    def __init__(self, concept, field, func=None):
        Mapping.__init__(self, concept, field, -2.0, -1.0)
        self.func = func
    def map(self, value, reverse=False, memo=None):
        if self.func:
            return [self.func(value, reverse)]
        else:
            return [value]
    def __str__(self):
        return "%s => %s" % (self.a, self.b)
    __repr__ = __str__

