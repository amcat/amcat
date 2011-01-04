from amcat.tools.cachable import cacher
from amcat.tools.cachable.latebind import LB
from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.tools import toolkit, idlabel

from datetime import datetime

import logging; log = logging.getLogger(__name__)

DUMMY_CLASSID_PARTYMEMBER = 1
DUMMY_CLASSID_OFFICE = 2
PERSONS_CLASSID = 4003
PARTYMEMBER_FUNCTIONID = 0

class Hierarchy(object):
    """
    Interface for hierarchies (ie classes and sets).
    Hierarchies should be consistent, ie the following should always be true:
    head(h.getRoots()).getParent() is None
    h.getParent(head(getChildren(o))) == o
    h.getParent(o) is None or head(h.getChildren(h.getParent(o))) == o
    Also, there should be no parent of child cycles, and every object in h must be reachable
    using repeated getChildren calls on the roots and vice versa
    """
    def getParent(self, object, date=None):
        """Returns a BoundObject representing the parent of the given (Bound)Object in this hierarchy"""
        abstract
    def getChildren(self, object):
        """
        Returns a sequence of BoundObjects representing the children of the given (Bound)Object in this hierarchy
        """
        abstract
    def getObjects(self):
        """Return a sequence of BoundObjects represnting all Objects in this hierarchy"""
        abstract
    def cacheHierarchy(self):
        """Optional  method to ask the Hierarchy to cache all objects and child/parent relations"""
        pass
    def getRoots(self):
        """returns a sequence of BoundObjects representing the root(s) of this hierarchy"""
        for o in self.getObjects():
            if not self.getParent(o):
                yield o
    def __contains__(self, object):
        """Checks whether the given (Bound)Object is included in this hierarchy"""
        abstract
    def getBoundObject(self, object_or_id):
        """Returns a BoundObject representing the given object (or objectid/boundobject)"""
        abstract
    def getClass(self, object):
        """Returns the Class object that is best seen as this objects class in this hierarchy"""
        abstract
        
    def getIndentedList(self, cachefirst = True):
        if cachefirst: self.cacheHierarchy()
        def recurse(o):
            yield o, 0
            for o2 in self.getChildren(o):
                for o3, i in recurse(o2):
                    yield o3, i+1
        for r in self.getRoots():
            for c, indent in recurse(r):
                yield c,indent

    def getCategorisationPath(self, object, date=None):
        object = self.getBoundObject(object) 
        p = object
        while True:
            p = self.getParent(p, date)
            if p is None: break
            yield p
                
    def categorise(self, object, date=None, depth=[0,1,2], returnObjects=True, returnOmklap=False):
        object = self.getBoundObject(object)
        if not object:
            path, omklap = [None for d in depth], 1.0
        else:
            log.debug("Getting categoriation path for %s/%s/%s, depth %s" % (self, object.id, str(object), depth))
            path = list(self.getCategorisationPath(object, date))
            if returnOmklap:
                omklap = 1
                for p, c in zip(path[1:-1], path[:-2]):
                    omklap *= self.getOmklap(p, c)
            if returnObjects:
                l = max(depth)+1
                path = [object] * (l - len(path)) + path #WvA moet dit niet max(path) zijn??
                path = [path[-1-d] for d in depth]

        if returnObjects and returnOmklap:
            return path, omklap
        elif returnOmklap:
            return omklap
        return path
    
    def getOmklap(self, parent, child):
        #TODO: lelijk!
        global _omklaps
        if _omklaps is None:
            _omklaps = set(self.db.doQuery("select classid, parentid, childid from o_hierarchy where reverse = 1"))
        clas = self.getClass(child)
        omklap = -1 if (clas.id, parent.id, child.id) in _omklaps else 1
        log.debug("omklap(%s, %s, %s) = %s" % (parent.idlabel(), child.idlabel(), clas.idlabel(), omklap))
               
        return omklap
            
_omklaps = None

class DictHierarchy(Hierarchy):
    """Abstract Hierarchy subclass that uses a dictionary to keep track of contained objects"""
    def __init__(self, *args, **kargs):
        Hierarchy.__init__(self, *args, **kargs)
        self.objectdict = None # {id : BoundObject}
    def __contains__(self, object):
        if object is None: return False
        if self.objectdict is None: self.cacheHierarchy()
        if type(object) <> int: object = object.id
        return object in self.objectdict
    def getBoundObject(self, object_or_id):
        if object_or_id is None: return
        if self.objectdict is None: self.cacheHierarchy()
        if type(object_or_id) <> int: object_or_id = object_or_id.id
        if object_or_id not in self.objectdict:
            toolkit.warn("Unknown objectid: %i" % object_or_id)
        return self.objectdict.get(object_or_id)
    def cacheHierarchy(self):
        if self.objectdict is not None: return
        self.objectdict = {}
        super(DictHierarchy, self).cacheHierarchy()
        for obj in self.objects:
            self.objectdict[obj.id] = BoundObject(self, obj)
    def getObjects(self):
        if self.objectdict is None: self.cacheHierarchy()
        return self.objectdict.values()
        

class BoundObject(idlabel.IDLabel):
    """
    Represents an object 'bound' to a hierachy, ie with a unique parent and sequence of children
    """
    def __init__(self, hierarchy, objekt):
        idlabel.IDLabel.__init__(self, objekt.id, label=None)
        self.hierarchy = hierarchy
        self.objekt = objekt
    def getParent(self, date=None):
        return self.hierarchy.getParent(self, date)
    def getChildren(self):
        return self.hierarchy.getChildren(self)
    @property
    def children(self):
        return self.getChildren()
    @property
    def parent(self):
        return self.getParent()
    @property
    def label(self):
        return self.objekt.label
    def __str__(self):
        return str(self.objekt)
    def getSearchString(self, *args, **kargs):
        return self.objekt.getSearchString( *args, **kargs)

class Tree(Cachable, DictHierarchy):
    __table__ = 'trees'
    __idcolumn__ = 'treeid'
    
    label = DBProperty()
    treeid = DBProperty()
    
    objects = ForeignKey(LB("Object", "object", "amcat.model.ontology"), table="trees_objects")
    
    def __init__(self, db, id, **cache):
        Cachable.__init__(self, db, id, **cache)
        DictHierarchy.__init__(self)
        
    @property
    def roots(self):
        self.cacheHierarchy()
        for o in self.getObjects():
            if not o.getParent():
                yield o
                
    def getChildren(self, object):
        if type(object) == BoundObject: object = object.objekt
        children = object.children.get(self, [])
        
        return (self.getBoundObject(c) for c in children)

    def getParent(self, object, date=None):
        if type(object) == BoundObject: object = object.objekt
        p = object.parents.get(self)
        if p:
            return self.getBoundObject(p)
    def cacheHierarchy(self):
        #cacher.cache(self.objects, "_parents", "_label", "_children")
        cacher.cache(self.objects, "_parents", "_children")
        super(Tree, self).cacheHierarchy()
  
