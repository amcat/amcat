from amcat.tools.cachable import cacher
from amcat.tools.cachable.latebind import LB
from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.model.ontology.tree import DictHierarchy, BoundObject

from datetime import datetime

import logging; log = logging.getLogger(__name__)

DUMMY_CLASSID_PARTYMEMBER = 1
DUMMY_CLASSID_OFFICE = 2
PERSONS_CLASSID = 4003
PARTYMEMBER_FUNCTIONID = 0

class Codebook(Cachable, DictHierarchy):
    __table__ = 'codebooks'
    __idcolumn__ = 'codebookid'
    
    name = DBProperty()
    
    objects = ForeignKey(LB("Object", "object", "amcat.model.ontology"), table="codebooks_objects", getcolumn="objectid")
    trees = ForeignKey(LB("Tree", "tree", "amcat.model.ontology"), table="codebooks_trees", getcolumn="treeid")
    
    def __init__(self, db, id, **cache):
        Cachable.__init__(self, db, id, **cache)
        DictHierarchy.__init__(self)
    def getParent(self, o, date=None):
        if type(o) == BoundObject: o = o.objekt 
        parents = dict(o.getAllParents(date))
        log.debug("%s.getParent(%s), parents=%s, trees=%s" % (self, o, ["%s:%s" % (k,v) for k,v in parents.iteritems()], map(str, self.trees)))
        for c in self.trees:
            if c not in parents: continue
            o2 = parents[c]
            if (o2 is None) or (o2 in self):
                log.debug(" --> %s from class %s" % (o2 and o2.idlabel(), c.idlabel()))
                return self.getBoundObject(o2)
    def getChildren(self, o):
        yielded = set()
        for c in self.trees:
            for o2 in c.getChildren(o):
                if o2 in yielded: continue
                if o2 not in self: continue
                # Make sure to return only children whose parent is o, ie if the child has a parent in more
                # trees in this set only return the child for the proper parent
                # ie satisfy [Assert(self.getParent(c) == o) for c in o.getChildren()]
                # TODO: WvA: isn't this guaranteed by iterating over the trees in order??
                p = self.getParent(o2)
                if p and p.id == o.id:
                    yielded.add(o2)
                    yield self.getBoundObject(o2)
                    
    def cacheHierarchy(self):
        cacher.cacheMultiple(self, "objects", "trees")
        #fields = ["_parents", "_children", "_label"]
        fields = ["_parents", "_children"]
        if set((DUMMY_CLASSID_PARTYMEMBER, DUMMY_CLASSID_OFFICE)) & set(c.id for c in self.trees):
            fields.append("functions")
        cacher.cacheMultiple(self.objects, *fields)
        for c in self.trees:
            c.cacheHierarchy() # TODO: only need membership
        super(Codebook, self).cacheHierarchy()
    def cacheLabels(self):
        #cacher.cache(self, objects=["_label"])
        pass
        
    def getClass(self, object):
        for c in self.trees:
            if object in c:
                return c
