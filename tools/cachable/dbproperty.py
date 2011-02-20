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

from __future__ import unicode_literals, print_function, absolute_import

import inspect, types
from amcat.tools import toolkit, idlabel
from amcat.tools.cachable.property import Property, UnknownTypeException
from amcat.tools.cachable.cachable import Cachable, _ensureTuple, _allowScalar
import logging; log = logging.getLogger(__name__)
from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()
def _dereferenceTargetClass(targetclass):
    if not callable(targetclass):
        raise ValueError("targetclass (%s) should be callable" % (targetclass))
    if not inspect.isclass(targetclass):
        # assume targetklass is lambda or latebind.LB, so dereference
        targetclass = targetclass()
    return targetclass

class DBProperty(Property):
    """Property that retrieves its value from the database"""

    def __init__(self, targetclass=None, table=None, getcolumn=None, refcolumn=None, constructor=None,
                 distinct=False,orderby=False, tablehook=None, **kargs):
        """
        @param targetclass: an optional (tuple of) target class to be used as constructor and for default table and getcolumn
        @param table: which table to query for this property
        @param getcolumn: the column(s) the select to get the value of this property
        @param refcolumn: the column(s) to use in the where clause to filter on the object's id
        @param contstructor: an optional function of (obj, db, value) to return the property value
        @param distinct: if true, select distinct rows
        @param orderby: an optional column to sort on when querying (mainly useful for one-to-many)
        @param tablehook: if given, a function that returns the 
        """
        Property.__init__(self, **kargs)
        self.targetclasses = targetclass
        self.table = table
        self.getcolumns = _ensureTuple(getcolumn)
        self.refcolumns = _ensureTuple(refcolumn)
        self.tablehook = tablehook # function obj -> table
        self.constructor = constructor # function(obj, db, values) -> child
        self.distinct = distinct
        self.orderby = orderby
        
    def _initialise(self, cls, propname):
        if self._initialised: return
        super(DBProperty, self)._initialise(cls, propname)
        if self.targetclasses:
            if type(self.targetclasses) in (list, tuple):
                self.targetclasses = tuple(_dereferenceTargetClass(tc) for tc in self.targetclasses)
            else:
                self.targetclasses = _ensureTuple(_dereferenceTargetClass(self.targetclasses))
    
    def dbrowToObject(self, obj, *dbvalues):
        """Convert a db row to an amcat object
        
        @param obj: the "parent object" of the new object
        @param dbvalues: the row tuple as returned from the db
        @return object: a single 'domain' object
        """
        #log.debug("Creating %r.%s object from %r, targetclass=%s, constructor=%s" % (obj, self, dbvalues, self.targetclass, self.constructor))
        if self.constructor:
            return self.constructor(obj, obj.db, *dbvalues)
        elif all(dbvalue is None for dbvalue in dbvalues):
            return None
        elif self.targetclasses:
            result = []
            for tc in self.targetclasses:
                if inspect.isclass(tc) and issubclass(tc, Cachable):
                    numcols = len(tc._getIDColumns())
                else:
                    numcols = 1
                                    
                vals, dbvalues = dbvalues[:numcols], dbvalues[numcols:]
                result.append(tc(obj.db, *vals))
            if dbvalues: raise ValueError("Mismatch between targetclasses (%r) ID columns and values, leftover: %r" %
                                          (self.targetclasses, dbvalues))
            return _allowScalar(tuple(result))
        else:
            return dbvalues[0]

    def objectToDbrow(self, obj):
        """Convert an amcat object to a db row
        
        @param obj: the "parent object" of the new object
        @param object: a single 'domain' object
        @return dbvalues: the row tuple as it was returned from the db
        """
        if isinstance(obj, Cachable):
            return obj._id
        
        if type(obj) not in (list, tuple): obj = (obj, )
        return obj

    def objectsToData(self, obj, objects):
        #log.debug("Serialising %s=%r" % (self, objects))
        return [self.objectToDbrow(objects)]
        
    def dataToObjects(self, obj, data):
        data = data[0] if data else [None]
        return self.dbrowToObject(obj, *data)
    
    def _getIDColumns(self):
        if self.refcolumns: return self.refcolumns
        return self.cls._getIDColumns()
    
    def _getTable(self, obj=None):
        #log.debug("getTable(%r), self.table=%s, self.tablehook=%s" % (obj, self.table, self.tablehook))
        if self.table: return self.table
        if self.tablehook: return self.tablehook(obj)
        if obj and getattr(obj,'__table__', None):
            return obj.__table__
        return self.cls.__table__
    
    def _getColumns(self):
        #log.debug("_getColumns, self=%r, getcolumns=%r, targetclasses=%r" % (self,self.getcolumns, self.targetclasses))
        if self.getcolumns: return self.getcolumns
        elif self.targetclasses:
            result =  toolkit.flatten(tc._getIDColumns() for tc in self.targetclasses)
            return result
        else:
            return (self.propname,)

    def retrieve(self, obj):
        """Use the database to retrieve the value of this property for obj
        """
        kargs = dict(orderby=self.orderby) if self.orderby else {}
        return obj.db.select(self._getTable(obj), self._getColumns(), obj._getWhere(self.refcolumns), alwaysReturnTable=True, distinct=self.distinct, **kargs)
    
    def getType(self, obj_or_db=None):
        # if we have targetclasses, return them/it
        if self.targetclasses:
            if len(self.targetclasses)==1: return self.targetclasses[0]
            return self.targetclasses
        try:
            return super(DBProperty, self).getType(obj_or_db)
        except UnknownTypeException:
            #unknown type, query db if available
            if not obj_or_db: raise
            if isinstance(obj_or_db, Cachable):
                db = obj_or_db.db
            else:
                db = obj_or_db
            self._observedType = db.getColumnType(self.cls.__table__, self.propname)
            return self._observedType

    def _update(self, db, obj, val):
        """Create and execute an SQL UPDATE statement to update the db"""
        #TODO: use serialisation method
        #log.debug("UPDATEing %r.%s -> %r" % (obj, self, val))
        if isinstance(val, idlabel.IDLabel): val = val.id
        cols = self._getColumns()
        vals = self.objectToDbrow(val)
        update = dict(toolkit.zipp(cols, vals))
        log.debug("UPDATEING %r.%s = %r -> cols=%r, vals=%r" % (obj, self, val, cols, vals)) 
        obj.db.update(self._getTable(obj), update, obj._getWhere(self.refcolumns))
        self.cache(obj, [vals], isData=True)


    def prepareCache(self, cacher):
        if self.tablehook: return # cannot cache as we don't know the table without getting the object!
        #log.info("%s: Adding %s.%s/%s to cacher" % (self, self._getTable(), self._getIDColumn(), self._getColumns()))
        cacher.addField(self._getColumns(), self._getTable(), self._getIDColumns(), self.orderby)

    def doCache(self, cacher, obj=None):
        if self.tablehook: return
        val = cacher.getFieldData(self._getColumns(), self._getTable(), obj, self.cls.__idcolumn__, self.orderby)
        #log.info("%s: Retrieved %s from cacher" % (self, val))
        self.cache(obj, val, isData=True)

    def isNullable(self):
        """Ask database whether this property is nullable"""
        if self._nullable is None:
            table = self._getTable(self.targetclasses)
            column = self._getColumns() 
            self._nullable = db.isNullable(table, column)
        return self._nullable
        
class ForeignKey(DBProperty):
    def __init__(self, targetclass=None, sequencetype=None, constructor=None, includeOwnID=False, **kargs):
        """Create a 'foreign key' property

        Getting the property will create a sequence of domain objects

        @param targetclass: the class of the domain objects, or None for keeping
          the db-primitive intact
        @param sequencetype: the type of sequence to create (list, set, etc), or
          None for returning a generator
        @param includeOwnID: if True, create objects using childid=(ownid,retrieved) 
        """
        DBProperty.__init__(self, targetclass, constructor=constructor, **kargs)
        self.sequencetype = sequencetype
        self.includeOwnID = includeOwnID


    def dataToObjects(self, obj, data):
        result = (self.dbrowToObject(obj, *row) for row in data)
        if self.sequencetype: result = self.sequencetype(result)
        return result


    def dbrowToObject(self, obj, *dbvalues):
        child = super(ForeignKey, self).dbrowToObject(obj, *dbvalues)
        # Try to set 'uplink', eg project1.articles[n].project = project1 
        uplinkprop = obj.__class__.__name__.lower()
        uplink = getattr(child.__class__, uplinkprop, None)
        if isinstance(uplink, Property):
            uplink.cache(child, obj)
                               
        return child

    
    def objectsToData(self, obj, objects):
        #log.debug("FKSerialising %s=%r" % (self, objects))
        return [self.objectToDbrow(o) for o in objects]
    
    def _getTable(self, obj=None):
        #log.debug("getTable(%r), self.table=%s, self.tablehook=%s" % (obj, self.table, self.tablehook))
        if self.table: return self.table
        if self.tablehook: return self.tablehook(obj)
        if self.targetclasses:
            if len(self.targetclasses) != 1:
                raise Exception("Cannot getTable from multiple targetclasses")
            return self.targetclasses[0].__table__
        return self.cls.__table__
        
    def isNullable(self, db):
        
        return True
    
    def getCardinality(self):
        if self.sequencetype is None:
            return types.GeneratorType
        return self.sequencetype

    def _update(self, db, obj, val):
        raise NotImplementedError()

    def addNewChild(self, db, obj, idvalues=None, **props):
        """Add a new child to this ForeignKey relation
        
        Note that the caller is responsible for maintaining the db transaction
        (i.e. for committing after an update).

        @param db: the database connection to use for updating/inserting
        @obj: the object (parent) to add the child to
        @props: **props to create a new instance (in addition to parent id)
        """
        if type(obj.__idcolumn__) in (list, tuple):
            props.update(dict(zip(obj.__idcolumn__, obj.id)))
        else:
            props[obj.__idcolumn__] = obj.id
        if len(self.targetclasses) > 1: raise Exception("Cannot create child with multiple targetclasses!")
        child = self.targetclasses[0].create(db, idvalues=idvalues, **props)
        #uncache to force retrieval, inefficient but for now easier than updating the cache?
        self.uncache(obj)
        return child

    def removeChild(self, db, obj, child):
        """Delete the child and remove it from this ForeignKey relation
        
        Note that the caller is responsible for maintaining the db transaction
        (i.e. for committing after an update).

        @param db: the database connection to use for updating/inserting
        @obj: the object (parent) to add the child to
        @child: the child to delete and remove
        """
        child.delete(db)
        #uncache to force retrieval, inefficient but for now easier than updating the cache?
        self.uncache(obj)

