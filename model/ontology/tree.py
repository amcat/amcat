from __future__ import unicode_literals, print_function, absolute_import
###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
Model module representing Trees of ontology Objects
"""

from amcat.tools.cachable import cacher
from amcat.tools.cachable.latebind import LB, MultiLB
from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.tools import idlabel

from amcat.model.ontology.hierarchy import Hierarchy, DictHierarchy

from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()

from datetime import datetime

import logging; log = logging.getLogger(__name__)

DUMMY_CLASSID_PARTYMEMBER = 1
DUMMY_CLASSID_OFFICE = 2
PERSONS_CLASSID = 4003
PARTYMEMBER_FUNCTIONID = 0



def boolmaker():
    return lambda obj, val: bool(val)

class Tree(Cachable, DictHierarchy):
    __table__ = 'trees'
    __idcolumn__ = 'treeid'
    
    label = DBProperty()
    treeid = DBProperty()
    
    objects = ForeignKey(MultiLB(LB("Object", sub="ontology"), LB("Object", sub="ontology")),
                         table="trees_objects", getcolumn=("objectid","parentid"),
                         sequencetype=dict)



    reverse = ForeignKey(MultiLB(LB("Object", sub="ontology"), boolmaker),
                         table="trees_objects", getcolumn=("objectid", "reverse"),
                         sequencetype=dict)

    
    
    def __init__(self, db, id, **cache):
        Cachable.__init__(self, db, id, **cache)
        Hierarchy.__init__(self, db)

    def _getParent(self, boundobject):
        return self.objects.get(boundobject.objekt)
    def _getObjects(self):
        return self.objects
    def _isReversed(self, boundobject):
        return self.reverse.get(boundobject.objekt)

    def _getAllObjects(self):
        for obj, parent in self.objects.iteritems():
            yield obj.id, parent and parent.id
    
    def cacheHierarchy(self):
        cacher.cache(self, "objects")
        log.debug("Cached!")
        super(Tree, self).cacheHierarchy()
    

def run():
    from amcat.db import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True)
    t = Tree(db, 4000)
    t.cacheHierarchy()
    from amcat.model.ontology import ontologytoolkit
    for i, o, r in ontologytoolkit.getIndentedList(t):
        print("  "*i, o.id)
        if i > 1: break
    db.printProfile()
        
if __name__ == '__main__':
    from amcat.tools.logging import amcatlogging;     amcatlogging.setup()

    db = dbtoolkit.amcatDB(profile=True)
    t = Tree(db, 4000)
    t.cacheHierarchy()
    from amcat.model.ontology import ontologytoolkit
    for i, o, r in ontologytoolkit.getIndentedList(t):
        print("  "*i, o.id)
        if i > 1: break
