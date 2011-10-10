from datetime import datetime
import collections

from amcat.tools import toolkit
from amcat.tools.model import AmcatModel
from amcat.model.ontology.hierarchy import DictHierarchy
from amcat.model.ontology.hierarchy import BoundCode

from django.db import models

import logging; log = logging.getLogger(__name__)

DUMMY_CLASSID_PARTYMEMBER = 1
DUMMY_CLASSID_OFFICE = 2
#PERSONS_CLASSID = 4003

class Codebook(AmcatModel, DictHierarchy):
    id = models.IntegerField(primary_key=True, db_column='codebook_id')

    name = models.TextField()
    codes = models.ManyToManyField("ontology.Code", db_table="codebooks_codes")
    #trees = models.ManyToManyField("Tree", through=CodebookTree)

    def __unicode__(self):
        return self.name

    class Meta():
        db_table = 'codebooks'
        app_label = 'ontology'

    def _getAllCodes(self):
        self.treesdict = collections.defaultdict(set) # treeid : codeids that got parent from tree
        seen = set()
        for t in self.trees:
            for obj, parent, reversed in t._getAllCodes():
                if obj not in seen:
                    self.treesdict[t.id].add(obj)
                    yield obj, parent, reversed
                    seen.add(obj)


    def getPath(self, code, date=None):
        """Check whether we need to use functions to categorise
        this code; if so, start super.getPath from function-parent
        and add to that path"""
        code =self.getCode(code)
        for t in self.trees:
            if code.id in self.treesdict[t.id]: 
                break # other class is first
            if t.id in (DUMMY_CLASSID_PARTYMEMBER, DUMMY_CLASSID_OFFICE):
                f = toolkit.head(code.objekt.currentFunctions(date, party=(t.id == DUMMY_CLASSID_PARTYMEMBER)))
                log.info("%r.%r.%r(%s) --> %s" % (self, t, code, date, f))
                if not f: continue
                f = f.office
                p = list(super(Codebook, self).getPath(f, date))
                return [(code, False)] + p
        return super(Codebook, self).getPath(code, date)
        
    def cacheLabels(self):
        for tree in self.trees:
            tree.cacheLabels()

    
    def getTree(self, code):
        """Return the Tree that gives this code its parent in this hierarchy"""
        for t in self.trees:
            if code in t: return t

class CodebookTree(AmcatModel):
    codebook = models.ForeignKey(Codebook)
    tree = models.ForeignKey("Tree")
    rank = models.IntegerField()

    class Meta():
        db_table = 'codebooks_trees'
        ordering = ('rank',)

def _getFunction(code, date, party=False):
    """Get a current function (wrt date) for code, if any
    accept party member function iff party is True"""
    for f in code.objekt.currentFunctions(date, party=party):
        return f.office
        
#from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()

