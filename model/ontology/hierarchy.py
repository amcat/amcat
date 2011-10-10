import collections
import logging; log = logging.getLogger(__name__)

from amcat.model.ontology.code import Code
from amcat.tools import idlabel, toolkit

from amcat.tools.logging import amcatlogging
#amcatlogging.infoModule()

class Hierarchy(object):
    """
    Interface for hierarchies (ie classes and sets).
    Hierarchies should be consistent, ie the following should always be true:
    all(x.getParent() is None for x in h.getRoots()) # all non-roots have a parent
    all(all(c.getParent==o for c in h.getChilden(o))
        for o in h.getCodes()) # every code is its childrens' parent
    all(h.getParent(o) is None or o in h.getChildren(h.getParent(o)) 
        for o in h.getCodes()) # all non-roots are the child of their parent  

    Also, there should be no parent of child cycles, and every code in h
    must be reachable using repeated getChildren calls on the roots and vice versa

    Subclasses *have* to implement _getParent and _getCodes
    """
    def __init__(self, db=None):
        self.db = db
        self._cachedPaths = {} # oid : path
    
    def getParent(self, code):
        """Returns the parent of code
        @type code: BoundCode, Code, or int
        @param code: the code whose children to return
        @return: sequence of BoundCode, or None if it is root
        """
        return self.getCode(self._getParent(self.getCode(code)))
    def _getParent(self, boundcode):
        raise NotImplementedError()
    
    def getChildren(self, code):
        """
        Returns a sequence of BoundCodes representing code's children
        @type code: BoundCode, Code, or int
        @param code: the code whose children to return
        @return: sequence of BoundCode
        """
        return (self.getCode(c)
                for c in self._getChildren(self.getCode(code)))
    def _getChildren(self, boundcode):
        """Base implementation to find children using getParent
        Subclasses should probably override this for efficiency"""
        for o in self.getCodes():
            if self.getParent(o) == boundcode:
                yield o
      
    def getCodes(self):
        """Return a sequence of BoundCodes represnting all Codes in this hierarchy"""
        return (self.getCode(o) for o in self._getCodes())
    def _getCodes(self):
        raise NotImplementedError()
    def __contains__(self, code):
        if code is None: return False
        return self.getCode(code) in self.getCodes()

    def isReversed(self, child):
        """Is the relation between this child and its parent reversed?"""
        return bool(self._isReversed(self.getCode(child)))
    def _isReversed(self, child):
        """Is this boundcode child's relation with its parent reversed?
        Default implementation returns False for all codes"""
        return False

    
    def getRoots(self):
        """returns a sequence of BoundCodes representing the root(s) of this hierarchy"""
        for o in self.getCodes():
            if not self.getParent(o):
                yield o
                
    def getCode(self, code_or_id):
        """Returns a BoundCode representing the given code

        @type code_or_id: BoundCode, Code, or int
        @param code_or_id: the code to get
        @return: BoundCode bound to this Hierarchy, or None if code_or_id is None"""
        if code_or_id is None: return None
        if isinstance(code_or_id, BoundCode):
            if code_or_id.hierarchy == self:
                return code_or_id
            code_or_id = code_or_id.objekt
        if not isinstance(code_or_id, Code):
            if not self.db: raise TypeError("Cannot create codes from int without database connectoin!")
            code_or_id = Code(self.db, code_or_id)
        return BoundCode(self, code_or_id)

    def cacheHierarchy(self):
       """Optional  method to ask the Hierarchy to cache all codes and child/parent relations"""
       pass


    def _calculatePath(self, code, date=None):
        reverse = False
        yield code, reverse
        parent = self.getParent(code)
        if not parent: return
        reverse = self.isReversed(code)
        for o, r in self.getPath(parent, date=date):
            yield o, r^reverse #^=XOR
    

    #def _calculatePath(self, code, date=None):        
    #    reverse = False
    #    while code:
    #        yield code, reverse
    #        reverse ^= self.isReversed(code) #XOR
    #        code = self.getParent(code)

    def getPath(self, code, date=None):
        code = self.getCode(code)
        try:
            return self._cachedPaths[code.id]        
        except KeyError:
            self._cachedPaths[code.id] = list(self._calculatePath(code, date))
            return self._cachedPaths[code.id]
            

                
    def categorise(self, code, date=None, depth=3, returnCode=True, returnReverse=False):
        # get categorisation path
        path = self.getPath(code, date)
        # pad / chop to correct length
        path = list(toolkit.pad(reversed(list(path)), depth, padwithlast=True))
        if returnCode and returnReverse:
            return path
        elif returnReverse:
            return [p[1] for p in path]
        else:
            return [p[0] for p in path]

    def cacheLabels(self):
        """Cache the labels for all codes in this hierarchy"""
        pass

    def getTree(self, code):
        """Return the Tree that gives this code its parent in this hierarchy"""
        raise NotImplementedError()
        

class DictHierarchy(Hierarchy):
    """Abstract Hierarchy subclass that uses a dictionary to keep track of contained codes

    subclasses should provide either _getCodes and _getParent or _getAllCodes
    """
    
    def cacheHierarchy(self):
        """Create code/parent dicts. Subclass should cache codes and .parent"""
        if hasattr(self, "codedict"): return
        log.debug("Caching hierarchy for %r/%r" % (id(self), self))
        self.codeset = set() # set of boundcodes that are 'in' this hierarchy
        self.codedict = {} # codeid -> boundcode for all requested codes
        self.parentdict = {} # boundcode child -> boundcode parent for non-roots
        self.childrendict = {} # boundcode parent -> set(children) for non-leaves
        self.reverseset = set() # set of boundcodes that are 'reversed' wrt their parents
        
        try: allcodes = self._getAllCodes()
        except NotImplementedError: allcodes = None

        log.info("Caching %r" % (self))
        
        if allcodes:
            # create dicts from allcodes
            for obj, parent, reversed in allcodes:
                obj, parent = map(self.getCode, (obj, parent))
                self.codeset.add(obj)
                if reversed: self.reverseset.add(obj)
                if parent:
                    self.parentdict[obj] = parent
                    if parent not in self.childrendict: self.childrendict[parent] = set()
                    self.childrendict[parent].add(obj)
            #log.info("Cached  %r, contains %r items" % (self, len(self.codeset)))
        else:
            # create codedict using _getCodes
            for obj in self._getCodes():
                obj = self.getCode(obj)
                self.codeset.add(obj)
                if self._isReversed(obj): self.reverseset.add(obj)
                parent = self.getCode(self._getParent(obj))
                if parent:
                    self.parentdict[obj] = parent
                    try:
                        self.childrendict[parent].add(obj)
                    except KeyError:
                        self.childrendict[parent] = set([obj])
        log.debug("Done with %r.cacheHiearchy" % self)
            
    def getCode(self, code_or_id):
        if code_or_id is None: return
        if not hasattr(self, "codedict"):self.cacheHierarchy()
        if type(code_or_id) <> int: code_or_id = code_or_id.id
        if code_or_id not in self.codedict:
            self.codedict[code_or_id] = super(DictHierarchy, self).getCode(code_or_id)
        return self.codedict[code_or_id]
    
    def getCodes(self):
        if not hasattr(self, "codedict"):self.cacheHierarchy()
        return self.codeset

    def getChildren(self, code):
        if not hasattr(self, "codedict"):self.cacheHierarchy()
        return self.childrendict.get(self.getCode(code), [])

    def getParent(self, code):
        if not hasattr(self, "codedict"):self.cacheHierarchy()
        return self.parentdict.get(self.getCode(code))

    def isReversed(self, code):
        if not hasattr(self, "codedict"):self.cacheHierarchy()
        return self.getCode(code) in self.reverseset
        
    
    def _getAllCodes(self):
        """Hook to provide codes and parents to the caching mechanism
        @return: sequence of (codeid, parentid, reversed) triples, with parentid None to
                  indicate roots
        """
        raise NotImplementedError()
        


    
class BoundCode(idlabel.Identity):
    """
    Represents an code 'bound' to a hierachy, ie with a unique parent and sequence of children
    """
    def __init__(self, hierarchy, objekt):
        idlabel.Identity.__init__(self, hierarchy, objekt)
        if not isinstance(objekt, Code) or not isinstance(hierarchy, Hierarchy):
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

