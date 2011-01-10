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

    def _getAllObjects(self):
        seen = set()
        for t in self.trees:
            for obj, parent, reversed in t._getAllObjects():
                if obj not in seen:
                    yield obj, parent, reversed
                    seen.add(obj)
        
from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()
