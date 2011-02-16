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

import logging; log = logging.getLogger(__name__)

from amcat.db import dbtoolkit
from amcat.tools import toolkit
import collections

from amcat.tools.cachable.property import Property
from amcat.tools.logging import amcatlogging
#amcatlogging.debugModule()

def sqlWhere(fields, ids):
    if type(fields) in (str, unicode):
        fields = [fields]
    if type(ids) not in (list, tuple):
        ids = [ids]

    return "(%s)" % " and ".join("(%s = %s)" % (field, dbtoolkit.quotesql(id))
                                 for (field, id) in zip(fields, ids))
        
def sqlFrom(cachables, table = None, reffield=None):
    log.debug("sqlFrom(table=%r, reffield=%r)" % (table, reffield))
    c = cachables[0] # prototype, assume all cachables are alike
    if reffield is None: reffield = c.__idcolumn__
    if type(reffield) in (str, unicode):
        if type(c.id) <> int:
            raise TypeError("Singular reffield with non-int id! Reffield: %r, cachable: %r, id: %r" % (reffield, c, c.id))
        where  = c.db.intSelectionSQL(reffield, (x.id for x in cachables))
    else:
        where = "((%s))" % ") or (".join(sqlWhere(reffield, x.id) for x in cachables)

    return " FROM %s WHERE %s" % (table or c.__table__, where)

class Cacher(object):
    """
    Object to gather data for multiple cachable objects and properties
    in as few SQL calls as possible
    """
    def __init__(self):
        self.fields = set() # (table, reffield, fields)
        
    def getData(self, db, cachables):
        self.data = collections.defaultdict(lambda  : collections.defaultdict(list)) # {table, reffield, fields, orderby} : {id : values}
        log.debug("Fields: %s" % self.fields)
        for table, reffield, fields, orderby in self.fields:
            select = reffield + fields
            for batch in toolkit.splitlist(cachables, 5000):
                SQL = "SELECT %s %s " % (",".join(map(db.escapeFieldName, select)), sqlFrom(batch, table, reffield))
                log.debug("Caching %s.%s (id=%s) with \n%s" % (table, fields, reffield, SQL))
                if orderby: SQL += " ORDER BY %s" % orderby
                for row in cachables[0].db.doQuery(SQL):
                    id, values = row[:len(reffield)], row[len(reffield):]
                    self.data[table, reffield,fields,orderby][id].append(values)
        log.debug("Cached Data = %r" % self.data)
            
    def addField(self, fields, table,  reffield, orderby):
        fields, reffield = map(_getTuple, (fields, reffield))
        log.debug("Adding field %s from %s (ref=%s)" % (fields, table, reffield))
        self.fields.add((table, reffield, fields, orderby))
    def getFieldData(self, fields, table, cachable, reffield, orderby):
        fields, reffield = map(_getTuple, (fields, reffield))
        id = cachable.id
        if type(id) not in (list, tuple): id = (id,)
        return self.data[table, reffield, fields, orderby].get(id, [])

def _getTuple(cols):
    if type(cols) in (str, unicode):
        return (cols,)
    elif type(cols) == tuple:
        return cols
    else:
        return tuple(cols)
    
def cacheMultiple(cachables, *propnames):
    """
    Cache the given propnames for the given cachables. If possible,
    uses a single SQL statement to cache for all objects.

    @param cachables: a sequence of cachables to cache. MUST all be of the same class
    @param propnames: the names of properties to cache on these cachables
    """
    if not cachables: return
    cachables = toolkit.getseq(cachables, seqtypes=list, convertscalar=True)
    classes = set(cachable.__class__ for cachable in cachables)
    if not len(classes): return
    if len(classes) != 1: raise Exception("cacheMultiple should receive only cachables of the same class! %r" % (classes))
    klass = toolkit.head(classes)
    
    cacher = Cacher()
    log.debug("cacheMultiple klass=%r, props=%r" % (klass, propnames))
    for propname in propnames:
        log.debug("Getting property %r" % propname)
        prop = getattr(klass, propname, None)
        if not isinstance(prop, Property): raise Exception("Cachable %r has not property %s" % (cachable, propname))
        prop.prepareCache(cacher)

    #toolkit.ticker.warn("Getting data")
    db = toolkit.head(cachables).db
    cacher.getData(db, cachables)

    #toolkit.ticker.warn("CAching values")
    for cachable in cachables:
        for prop in propnames:
            getattr(cachable.__class__, prop).doCache(cacher, cachable)

    for prop in propnames:
	getattr(cachable.__class__, prop).cachePerObject(db, cachables)

def cache(cachables, *properties, **structure):
    """
    Cache properties and properties of (foreign key) properties
    Structure is a dict where the keys are properties of the cachable,
    If the property itself returns a (sequence of) cachable,
    the value in the structure can be a structure dict which is
    cached recursively on the retrieved cachable object(s).
    If the structure dictionary value is False (None, {}, ...), only
    the property itself is retrieved. *properties are treated as structure
    keys with a False value.
    example: cache([article1, article2], "headline", source=["name"])
             Caches the headline and source of these articles, and also
             caches the name of the source(s). 
    """
    # insert bare properties into structure, make surce cachables is iterable
    if len(properties)==1 and toolkit.isSequence(properties[0], excludeStrings=True): properties = properties[0]
    for prop in properties: structure[prop] = None
    if not toolkit.isIterable(cachables, excludeStrings=True): cachables = [cachables]
    # cache first layer
    cacheMultiple(cachables, *structure.keys())
    # recurse into next layer
    for prop, struct in structure.iteritems():
        if struct:
            objects = set()
            for c in cachables:
                addendum = c.__getattribute__(prop)
                if not toolkit.isIterable(addendum, excludeStrings=False): addendum=[addendum]
                objects |= set(a for a in addendum if a)
            if type(struct) <> dict: struct = dict((k, False) for k in struct)
            cache(objects, **struct)
    
            
