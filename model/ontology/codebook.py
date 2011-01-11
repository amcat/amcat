from datetime import datetime
import collections
import logging; log = logging.getLogger(__name__)

from amcat.tools.cachable import cacher
from amcat.tools.cachable.latebind import LB
from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.model.ontology.hierarchy import DictHierarchy
from amcat.model.ontology.hierarchy import BoundObject

DUMMY_CLASSID_PARTYMEMBER = 1
DUMMY_CLASSID_OFFICE = 2
PARTYMEMBER_FUNCTIONID = 0

#PERSONS_CLASSID = 4003


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
	self.treesdict = collections.defaultdict(set) # treeid : objectids that got parent from tree
        seen = set()
        for t in self.trees:
            for obj, parent, reversed in t._getAllObjects():
                if obj not in seen:
		    self.treesdict[t.id].add(obj)
                    yield obj, parent, reversed
                    seen.add(obj)


    def getPath(self, object, date=None):
	"""Check whether we need to use functions to categorise
	this object; if so, start super.getPath from function-parent
	and add to that path"""
	object =self.getObject(object)
	for t in self.trees:
	    if object.id in self.treesdict[t.id]: 
		break # other class is first
	    if t.id in (DUMMY_CLASSID_PARTYMEMBER, DUMMY_CLASSID_OFFICE):
		f = _getFunction(object, date, t.id == DUMMY_CLASSID_PARTYMEMBER)
		log.info("%r.%r.%r(%s) --> %s" % (self, t, object, date, f))
		if not f: continue
		p = list(super(Codebook, self).getPath(f, date))
		return [(object, False)] + p
	return super(Codebook, self).getPath(object, date)

def _getFunction(object, date, party=False):
    """Get a current function (wrt date) for object, if any
    accept party member function iff party is True"""
    for f in object.objekt.currentFunctions(date):
	isparty = f.functionid == PARTYMEMBER_FUNCTIONID
	if party != isparty: continue
	return f.office
        
#from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()

