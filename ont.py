from cachable2 import Cachable, DBProperty, ForeignKey, DBProperties
from datetime import datetime
import cachable

import toolkit, idlabel, language
import logging; log = logging.getLogger(__name__)

DUMMY_CLASSID_PARTYMEMBER = 1
DUMMY_CLASSID_OFFICE = 2
PERSONS_CLASSID = 4003
PARTYMEMBER_FUNCTIONID = 0

def cache(*a, **k):
    pass
    
def getParent(obj, db, cid, pid):
    cl = Class(db, cid)
    if pid is None:
        return cl, None
    return cl, Object(db, pid)

    #return Class(db, cid), pid and Object(db, pid)

def getAllAncestors(object, stoplist=None, golist=None):
    if stoplist is None: stoplist = set()
    for p in object.getAllParents():
        if (p is None) or (p in stoplist): continue
        if (golist and p not in golist): continue
        yield p
        stoplist.add(p)
        for o2 in getAllAncestors(p, stoplist, golist):
            yield o2

def getAllDescendants(object, stoplist=None, golist=None):
    if stoplist is None: stoplist = set()
    children = object.children
    if not children: return
    for p in children:
        if (p is None) or (p in stoplist): continue
        if (golist and p not in golist): continue
        yield p
        stoplist.add(p)
        for o2 in getAllDescendants(p, stoplist, golist):
            yield o2

class Function(Cachable):
    __table__ = "o_politicians_functions"
    __idcolumn__ = ("functionid", "office_objectid", "fromdate", "todate")
    
    functionid, todate = DBProperties(2)
    _fromdate = DBProperty(getcolumn="fromdate")
    office = DBProperty(lambda:Object, refcolumn="office_objectid")
    
    @property
    def fromdate(self):
        if self._fromdate.year != 1753:
            return self._fromdate
        
    @property
    def klass(self):
        return Class(db, 1) if self.functionid==0 else Class(db, 2)
    
class Label(Cachable):
    __table__ = 'o_labels'
    __idcolumn__ = ('objectid', 'languageid')
    __label__ = 'label'
    
    label, objectid, languageid = DBProperties(3)
    
    language = DBProperty(lambda:language.Language)
    
class Politician(Cachable):
    __table__ = 'o_politicians'
    __idcolumn__ = 'objectid'
    
    name, firstname, initials, prefix = DBProperties(4)
    title, birthdate, birthplace, male = DBProperties(4)
    
    functions = ForeignKey(Function)
    object = DBProperty(lambda:Object)

class Object(Cachable):
    __table__ = 'o_objects'
    __idcolumn__ = 'objectid'
    
    labels = ForeignKey(lambda:Label)
    
    _parents = ForeignKey(table="o_hierarchy", getcolumn=("classid", "parentid"), refcolumn="childid", constructor=getParent)
    _children = ForeignKey(table="o_hierarchy", getcolumn=("classid", "childid"), refcolumn="parentid", constructor=getParent)
    
    @property
    def parents(self):
        return dict(self._parents)
    
    @property
    def children(self):
        return toolkit.multidict(self._children)
    
    @property
    def label(self):
        try:
            return self.labels.next().label
        except StopIteration:
            return 'GEEN LABEL: FIXME'
    
    # Move to separate class?
    name = DBProperty(table="o_politicians")
    firstname = DBProperty(table="o_politicians")
    prefix = DBProperty(table="o_politicians")
    keyword = DBProperty(table="o_keywords")
    male = DBProperty(table="o_politicians")
    
    functions = ForeignKey(lambda:Function)

    def getAllParents(self, date=None):
        for c, p in self.parents.iteritems():
            yield c, p
        for f in self.currentFunctions(date):
            yield f.klass, f.office
        
    def currentFunctions(self, date=None):
        if not date: date = datetime.now()
        for f in self.functions:
            if f.fromdate and toolkit.cmpDate(date, f.fromdate) < 0: continue
            if f.todate and toolkit.cmpDate(date, f.todate) >= 0: continue
            yield f
    
    def getSearchString(self, date=None, xapian=False, languageid=None, fallback=False):
        """Returns the search string for this object.
        date: if given, use only functions active on this date
        xapian: if true, do not use ^0 weights
        languageid: if given, use labels.get(languageid) rather than o_keywords"""
        
        if not date: date = datetime.now()
        if languageid:
            kw = self.getLabel(languageid)

        if (not languageid) or (fallback and kw is None):
            kw = self.keyword
        
        if not kw and self.name:
            ln = self.name
            if "-" in ln or " " in ln:
                ln = '"%s"' % ln.replace("-", " ")
            conds = []
            if self.firstname:
                conds.append(self.firstname)
            for function in self.currentFunctions(date):
                k = function.office.getSearchString()
                if not k: k = '"%s"' % str(function.office).replace("-"," ")
                conds.append(k)
                conds += function2conds(function)
            if conds:
                if xapian:
                    kw = "%s AND (%s)" % (ln, " OR ".join("%s" % x.strip() for x in conds),)
                else:
                    kw = "%s AND (%s)" % (ln, " OR ".join("%s^0" % x.strip() for x in conds),)
            else:
                kw = ln
        if kw:
            if type(kw) == str: kw = kw.decode('latin-1')
            return kw.replace("\n"," ")


def function2conds(function):
    officeid = function.office.id
    if officeid in (380, 707, 729, 1146, 1536, 1924, 2054, 2405, 2411, 2554, 2643):
        if function.functionid == 2:
            return ["bewinds*", "minister*"]
        else:
            return ["bewinds*", "staatssecret*"]

    if officeid == 901:
        return ["premier", '"minister president"']
    if officeid == 548:
        return ["senator", '"eerste kamer*"']
    if officeid == 1608:
        return ["parlement*", '"tweede kamer*"']
    if officeid == 2087:
        return ['"europ* parlement*"', "europarle*"]
    return []


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

class Class(Cachable, DictHierarchy):
    __table__ = 'o_classes'
    __idcolumn__ = 'classid'
    __label__ = "label"
    
    label = DBProperty()
    classid = DBProperty()
    
    objects = ForeignKey(lambda: Object, table="o_hierarchy", getcolumn="childid")
    
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
        cache(self.objects, "parents", "label", "children")
        super(Class, self).cacheHierarchy()
        
class Set(Cachable, DictHierarchy):
    __table__ = 'o_sets'
    __idcolumn__ = 'setid'
    
    name = DBProperty()
    
    objects = ForeignKey(lambda: Object, table="o_sets_objects", getcolumn="objectid")
    classes = ForeignKey(lambda: Class, table="o_sets_classes", getcolumn="classid")
    
    def __init__(self, db, id, **cache):
        Cachable.__init__(self, db, id, **cache)
        DictHierarchy.__init__(self)
    def getParent(self, o, date=None):
        if type(o) == BoundObject: o = o.objekt 
        parents = dict(o.getAllParents(date))
        log.debug("%s.getParent(%s), parents=%s, classes=%s" % (self, o, ["%s:%s" % (k,v) for k,v in parents.iteritems()], map(str, self.classes)))
        for c in self.classes:
            if c not in parents: continue
            o2 = parents[c]
            if (o2 is None) or (o2 in self):
                log.debug(" --> %s from class %s" % (o2 and o2.idlabel(), c.idlabel()))
                return self.getBoundObject(o2)
    def getChildren(self, o):
        yielded = set()
        for c in self.classes:
            for o2 in c.getChildren(o):
                if o2 in yielded: continue
                if o2 not in self: continue
                # Make sure to return only children whose parent is o, ie if the child has a parent in more
                # classes in this set only return the child for the proper parent
                # ie satisfy [Assert(self.getParent(c) == o) for c in o.getChildren()]
                # TODO: WvA: isn't this guaranteed by iterating over the classes in order??
                p = self.getParent(o2)
                if p and p.id == o.id:
                    yielded.add(o2)
                    yield self.getBoundObject(o2)
                    
    def cacheHierarchy(self):
        cachable.cacheMultiple(self, "objects", "classes")
        fields = ["parents", "children", "label"]
        if set((DUMMY_CLASSID_PARTYMEMBER, DUMMY_CLASSID_OFFICE)) & set(c.id for c in self.classes):
            fields.append("functions")
        cachable.cacheMultiple(self.objects, *fields)
        for c in self.classes:
            c.cacheHierarchy() # TODO: only need membership
        super(Set, self).cacheHierarchy()
    def cacheLabels(self):
        cachable.cache(self, objects=["label"])
        
    def getClass(self, object):
        for c in self.classes:
            if object in c:
                return c

if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True)
    
    o = Object(db, 644)
    print o.getSearchString()
    print list(o.currentFunctions())
    
    s = Set(db, 2)
    print list(s.objects)

    #o = createPolitician(db, "hoof", 1373, "piet", prefix="van")

