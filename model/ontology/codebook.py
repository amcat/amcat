from amcat.tools.cachable import cacher
from amcat.tools.cachable.latebind import LB
from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.model.ontology.hierarchy import DictHierarchy
from amcat.model.ontology.hierarchy import BoundObject

from datetime import datetime

import logging; log = logging.getLogger(__name__)

DUMMY_CLASSID_PARTYMEMBER = 1
DUMMY_CLASSID_OFFICE = 2
PERSONS_CLASSID = 4003
PARTYMEMBER_FUNCTIONID = 0

class Codebook(Cachable, DictHierarchy):
    __table__ = 'codebooks'
    __idcolumn__ = 'codebookid'
    __labelprop__ = 'name'
    name = DBProperty()
    
    objects = ForeignKey(LB("Object", sub="ontology"), table="codebooks_objects")
    trees = ForeignKey(LB("Tree", sub="ontology"), table="codebooks_trees", orderby="rank")
    
    def __init__(self, db, id, **cache):
        Cachable.__init__(self, db, id, **cache)
        DictHierarchy.__init__(self, db)
    def _getParent(self, o):
        for t in self.trees:
            if o in t:
                return t.getParent(o)
    def _getObjects(self):
        return self.objects
                    
    def cacheHierarchy(self):
        log.debug("Caching %r" % self)
        cacher.cache(self, "objects", "trees")
        for t in self.trees:
            #log.debug("Caching %r" % t)
            t.cacheHierarchy()
#TODO!        if set((DUMMY_CLASSID_PARTYMEMBER, DUMMY_CLASSID_OFFICE)) & set(c.id for c in self.trees):
        log.debug("Caching %r.super" % self)
        super(Codebook, self).cacheHierarchy()
        log.debug("Done caching %r" % self)

from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()
