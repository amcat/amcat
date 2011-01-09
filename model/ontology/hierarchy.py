import collections
import logging; log = logging.getLogger(__name__)

from amcat.model.ontology.object import Object
from amcat.tools import idlabel, toolkit

from amcat.tools.logging import amcatlogging
amcatlogging.debugModule()

class Hierarchy(object):
    """
    Interface for hierarchies (ie classes and sets).
    Hierarchies should be consistent, ie the following should always be true:
    all(x.getParent() is None for x in h.getRoots()) # all non-roots have a parent
    all(all(c.getParent==o for c in h.getChilden(o))
        for o in h.getObjects()) # every object is its childrens' parent
    all(h.getParent(o) is None or o in h.getChildren(h.getParent(o)) 
        for o in h.getObjects()) # all non-roots are the child of their parent  

    Also, there should be no parent of child cycles, and every object in h
    must be reachable using repeated getChildren calls on the roots and vice versa

    Subclasses *have* to implement _getParent and _getObjects
    """
    def __init__(self, db=None):
        self.db = db
    
    def getParent(self, object):
        """Returns the parent of object
        @type object: BoundObject, Object, or int
        @param object: the object whose children to return
        @return: sequence of BoundObject, or None if it is root
        """
        return self.getObject(self._getParent(self.getObject(object)))
    def _getParent(self, boundobject):
        raise NotImplementedError()
    
    def getChildren(self, object):
        """
        Returns a sequence of BoundObjects representing object's children
        @type object: BoundObject, Object, or int
        @param object: the object whose children to return
        @return: sequence of BoundObject
        """
        return (self.getObject(c)
                for c in self._getChildren(self.getObject(object)))
    def _getChildren(self, boundobject):
        """Base implementation to find children using getParent
        Subclasses should probably override this for efficiency"""
        for o in self.getObjects():
            if self.getParent(o) == boundobject:
                yield o
      
    def getObjects(self):
        """Return a sequence of BoundObjects represnting all Objects in this hierarchy"""
        return (self.getObject(o) for o in self._getObjects())
    def _getObjects(self):
        raise NotImplementedError()
    def __contains__(self, object):
        if object is None: return False
        return self.getObject(object) in self.getObjects()

    def isReversed(self, child):
        """Is the relation between this child and its parent reversed?"""
        return bool(self._isReversed(self.getObject(child)))
    def _isReversed(self, child):
        """Is this boundobject child's relation with its parent reversed?
        Default implementation returns False for all objects"""
        return False

    
    def getRoots(self):
        """returns a sequence of BoundObjects representing the root(s) of this hierarchy"""
        for o in self.getObjects():
            if not self.getParent(o):
                yield o
                
    def getObject(self, object_or_id):
        """Returns a BoundObject representing the given object

        @type object_or_id: BoundObject, Object, or int
        @param object_or_id: the object to get
        @return: BoundObject bound to this Hierarchy, or None if object_or_id is None"""
        if object_or_id is None: return None
        if isinstance(object_or_id, BoundObject):
            if object_or_id.hierarchy == self:
                return object_or_id
            object_or_id = object_or_id.objekt
        if not isinstance(object_or_id, Object):
            if not self.db: raise TypeError("Cannot create objects from int without database connectoin!")
            object_or_id = Object(self.db, object_or_id)
        return BoundObject(self, object_or_id)

    def cacheHierarchy(self):
       """Optional  method to ask the Hierarchy to cache all objects and child/parent relations"""
       pass
    
    def getPath(self, object, date=None):
        reverse = False
        yield self.getObject(object),  reverse
        while True:
            reverse ^= self.isReversed(object) #XOR
            object = self.getParent(object)
            if object is None: break
            yield object, reverse
                
    def categorise(self, object, date=None, depth=3, returnObject=True, returnReverse=False):
        # get categorisation path
        path = list(reversed(list(self.getPath(object, date)))) # list(.(list(.)) efficient?
        # pad / chop to correct length
        path = toolkit.pad(path, depth, padwith=path[-1])
        if returnObject and returnReverse:
            return path
        elif returnReverse:
            return [p[1] for p in path]
        else:
            return [p[0] for p in path]


class DictHierarchy(Hierarchy):
    """Abstract Hierarchy subclass that uses a dictionary to keep track of contained objects

    subclasses should provide either _getObjects and _getParent or _getAllObjects
    """
    
    def cacheHierarchy(self):
        """Create object/parent dicts. Subclass should cache objects and .parent"""
        if hasattr(self, "objectdict"): return
        log.debug("Caching hierarchy for %r/%r" % (id(self), self))
        self.objectdict, self.parentdict, self.childrendict  = {}, {}, {}
        
        try: allobjects = self._getAllObjects()
        except NotImplementedError: allobjects = None

        log.debug("allobjects? %r" % bool(allobjects))
        
        if allobjects:
            # create dicts from allobjects
            def getObject(o):
                if type(o) == int:
                    if o not in self.objectdict:
                        self.objectdict[o] = super(DictHierarchy, self).getObject(o)
                    o = self.objectdict[o]
                return o
            
            for obj, parent in allobjects:
                obj, parent = map(getObject, (obj, parent))
                if parent:
                    self.parentdict[obj] = parent
                    if parent not in self.childrendict: self.childrendict[parent] = set()
                    self.childrendict[parent].add(obj)
        else:
            # create objectdict using _getObjects
            for obj in self._getObjects():
                obj = super(DictHierarchy, self).getObject(obj)
                self.objectdict[obj.id] = obj
                self.childrendict[obj] = set()
            # can now use self.getObject(s) as objectdict is filled
            for obj in self.getObjects():
                parent = self.getObject(self._getParent(obj))
                if parent:
                    self.parentdict[obj] = parent
                    self.childrendict[parent].add(obj)
        log.debug("Done with %r.cacheHiearchy" % self)
            
    def getObject(self, object_or_id):
        if object_or_id is None: return
        if not hasattr(self, "objectdict"):self.cacheHierarchy()
        if type(object_or_id) <> int: object_or_id = object_or_id.id
        return self.objectdict.get(object_or_id)
    
    def getObjects(self):
        if not hasattr(self, "objectdict"):self.cacheHierarchy()
        return self.childrendict # will iterate over keys, so as good as a set?

    def getChildren(self, object):
        if not hasattr(self, "objectdict"):self.cacheHierarchy()
        return self.childrendict.get(self.getObject(object), [])

    def getParent(self, object):
        if not hasattr(self, "objectdict"):self.cacheHierarchy()
        return self.parentdict.get(self.getObject(object))

    def _getAllObjects(self):
        """Hook to provide objects and parents to the caching mechanism
        @return: sequence of (objectid, parentid) pairs, with parentid None to
                  indicate roots
        """
        raise NotImplementedError()
        


    
class BoundObject(idlabel.Identity):
    """
    Represents an object 'bound' to a hierachy, ie with a unique parent and sequence of children
    """
    def __init__(self, hierarchy, objekt):
        idlabel.Identity.__init__(self, hierarchy, objekt)
        if not isinstance(objekt, Object) or not isinstance(hierarchy, Hierarchy):
            raise TypeError("Cannot bind %s to %s" % (type(objekt), type(hierarchy)))
        self.hierarchy = hierarchy
        self.objekt = objekt
    def getParent(self):
        return self.hierarchy.getParent(self)
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
    @property
    def id(self):
        return self.objekt.id
    def __str__(self):
        return str(self.objekt)
    def getSearchString(self, *args, **kargs):
        return self.objekt.getSearchString( *args, **kargs)

