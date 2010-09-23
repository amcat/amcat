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
Module to implement domain objects by assuming
- it uses a database to retrieve its values
- it uses a memcache to store cached values

The main idea behind cachable is that defining and using domain objects
should be as simple as possible. This is done by overriding the instance
attribute accessing (__getattribute__ etc.) in the class, and transparantly
fetching uncached values from the underlying database. 

Example usage::

  class MyObject(Cachable):
    __table__ = 'objects'
    __idcolumn__ = 'objectid'
    label = DBProperty()

  o = MyObject(db, id)
  print o.label    # will be retrieve from db
  print o.label    # from cache
  del o.label      # uncached
  o.label = 'test' # manually set cache
  print o.label    # 'test' from cache
"""

import inspect, types, warnings
import idlabel, dbtoolkit
import amcatmemcache as store
from toolkit import printargs


class Meta(type):
    """Metaclass to  ensure properties are initialised"""
    def __getattribute__(cls, attr):
        result = type.__getattribute__(cls, attr)
        if isinstance(result, Property):
            if not result._initialised: result._initialise(cls, attr)
        return result

class Cachable(idlabel.IDLabel):
    __metaclass__ = Meta
    """Main class of the Cachable structure
    
    A Cachable class has class-level properties that are 
    connected to a backing store from which they get/set 
    (class_property_id):value pairs

    Cachable works by overriding the __getattribute__, __setattr__,
    and __delattr__ methods. These methods now check whether the
    attribute is a property, and if so call get/set/del on the property    
    """
    
    def __init__(self, db, id):
        """Create a cachable with db and id
        
        @param db: database connection
        @param id: the id of this object
        """
        if id is None: raise ValueError("ID should not be None!")
        if db is None: raise ValueError("DB should not be None!")
        self.db = db
        idlabel.IDLabel.__init__(self, id)

    @classmethod
    def _getProperty(cls, attr):
       """return a Property attr if there is one, TypeError (or AttributeError) otherwise"""
       p = getattr(cls, attr)
       if isinstance(p, Property):
           return p
       raise TypeError("%s is not a Property" % attr)
    
    def __getattribute__(self, attr):
        """if attr exists and is a property, use its .get method. Otherwise, call super"""
        if not "_" in attr:
            try:
                p =  self.__class__._getProperty(attr)
            except (TypeError, AttributeError):
                pass
            else:
                return p.get(self)
        return super(Cachable, self).__getattribute__(attr)
    

    def __setattr__(self, attr, value):
        """If attr is a property, cache the value. Otherwise, call super"""
        try:
            p = self._getProperty(attr)
        except (TypeError, AttributeError):
            super(Cachable, self).__setattr__(attr, value)
        else:
            p.cache(self, value)

    def __delattr__(self, attr):
        """If attr is a property, uncache the value. Otherwise, call super"""
        try:
            p = self._getProperty(attr)
        except (TypeError, AttributeError):
            super(Cachable, self).__delattr__(attr)
        else:
            p.uncache(self)

    def getType(self, prop):
        """Get the type of the given property (or property name)"""
        if not isinstance(prop, Property):
            prop = self._getProperty(prop)
        return prop.getType(self)

    @property
    def label(self):
        # if a __labelprop__ is defined, return that, otherwise, call super
        try:
            return getattr(self, self.__labelprop__)
        except AttributeError:
            return super(Cachable, self).label
    
            
class UnknownTypeException(Exception):
    def __init__(self, prop):
        Exception.__init__(self, "The type of property %s cannot be determined" % prop)

class Property(object):
    """Abstract base class of all Properties. 

    Subclasses should implement retrieve(obj)
    """
    
    def __init__(self, deprecated=False):
        self._initialised = False
        self.observedType = None
        self.deprecated = deprecated
        
    def _initialise(self, cls, propname):
        """initialise this property with the given class and propname

        Properties are initialised for two reasons:
        - to 'bind' it to class and propname (which are not accessible on creation)
        - to allow resolving types that would cause import problems on creation
        """
        self.cls = cls
        self.propname = propname
        self.store = store.CachablePropertyStore(cls, propname)
        self._initialised = True

    def get(self, obj):
        """Get obj from cache, or L{retrieve} and L{cache} it

        Will call L{dataToObjects} to deserialise the value"""
        if self.deprecated:
            warnings.warn(DeprecationWarning("Property %s has been deprecated" % self))
        try:
            v = self.getCached(obj)
        except store.UnknownKeyException:
            v = self.retrieve(obj)
            self.cache(obj, v)
        v = self.dataToObjects(obj, v)
        # remember the type info for later use
        if self.observedType is None: self.observedType = type(v)
        return v

    def dataToObjects(self, obj, data):
        """Deserialise the data into object(s)

        @param obj: the 'parent' object of the new object(s)
        @param data: the raw data (from the db or memcache)
        @return: an (iterable of) 'domain' object(s)
        """
        return data
    
    def cache(self, obj, value):
        """Cache the given value for the given object"""
        self.store.set(obj.id, value)
    def uncache(self, obj):
        """Uncache the given value for the given object"""
        self.store.delete(obj.id)
    def getCached(self, obj): 
        """Get the cached value for obj, or raise an UnknownKeyException"""
        return self.store.get(obj.id)

    def retrieve(self, obj): 
        """Get the value for this property from the underlying data source
        
        B{Abstract: Subclasses should override} 
        """
        abstract

    def getType(self, obj=None):
        """Get the data type of this property

        @param obj: an optional Cachable object
          that can be used to help determine the type
        @return a type object  
        """
        if (self.observedType is None
            and isinstance(obj, Cachable)):
            #try to get cached value
            try:
                val = self.getCached(obj)
                self.observedType = type(val)
            except store.UnknownKeyException:
                pass
        if self.observedType is None:
            raise UnknownTypeException(self)
        return self.observedType        
                
    def getCardinality(self): 
        """Get the cardinality of this property

        @return None for single values, a sequence type for multiple values
        """
        return None
    def __str__(self):
        try:
            return "%s(%s.%s)" % (self.__class__.__name__, self.cls.__name__, self.propname)
        except AttributeError:
            return "%s(uninitialised)" %  (self.__class__.__name__,)
        
class DBProperty(Property):
    """Property that retrieves its value from the database"""

    def __init__(self, targetclass=None, table=None, getcolumn=None, **kargs):
        Property.__init__(self, **kargs)
        self.targetclass = targetclass
        self.table = table
        self.getcolumn = getcolumn
    def _initialise(self, cls, propname):
        super(DBProperty, self)._initialise(cls, propname)
        if self.targetclass is not None:
            if not callable(self.targetclass):
                raise ValueError("targetklass should be callable")
            if ((not inspect.isclass(self.targetclass)) and
                inspect.getargspec(self.targetclass)[0] == []):
                # assume targetklass is lambda
                self.targetclass = self.targetclass()

    def dbrowToObject(self, obj, *dbvalues):
        """Convert a db row to an amcat object
        
        @param obj: the "parent object" of the new object
        @param dbvalues: the row tuple as returned from the db
        @return object: a single 'domain' object
        """
        if self.targetclass:
            if dbvalues == (None,) * len(dbvalues): 
                return None
            if type(self.targetclass) == tuple:
                if len(self.targetclass) != len(dbvalues):
                    raise ValueError("If targetclass is a tuple, #columns should equal #classes")
                return tuple(c(obj.db, v) for (c, v) in zip(self.targetclass, dbvalues))
            else:
                return self.targetclass(obj.db, *dbvalues)
        return dbvalues[0]

    def dataToObjects(self, obj, data):
        return self.dbrowToObject(obj, *data[0])

    def _getTable(self):
        if self.table: return self.table
        return self.cls.__table__
    def _getColumns(self):
        if self.getcolumn: return self.getcolumn
        try:
            if type(self.targetclass) == tuple:
                return tuple(c.__idcolumn__ for c in self.targetclass)
            return self.targetclass.__idcolumn__
        except AttributeError:
            return self.propname
    
    def retrieve(self, obj):
        """Use the database to retrieve the value of this property for obj
        Calls dbresultToObjects on the db results
        """
        return _select(self._getColumns(), obj, self._getTable())
    
    def getType(self, obj_or_db=None):
        # if targetclass is a class or tuple of classes, return it 
        if inspect.isclass(self.targetclass): return self.targetclass
        if (type(self.targetclass) == tuple and all(inspect.isclass(c) for c in self.targetclass)):
            return self.targetclass
        
        try:
            return super(DBProperty, self).getType(obj_or_db)
        except UnknownTypeException:
            if not obj_or_db: raise
        if isinstance(obj_or_db, Cachable):
            db = obj_or_db.db
        else:
            db = obj_or_db
        result = db.getColumnType(self.cls.__table__, self.propname)
        self.observedType = result
        return result

class ForeignKey(DBProperty):
    def __init__(self, targetclass=None, sequencetype=None, **kargs):
        """Create a 'foreign key' property

        Getting the property will create a sequence of domain objects

        @param targetclass: the class of the domain objects, or None for keeping
          the db-primitive intact
        @param sequencetype: the type of sequence to create (list, set, etc), or
          None for returning a generator
        """
        DBProperty.__init__(self, targetclass, **kargs)
        self.sequencetype = sequencetype

    def dataToObjects(self, obj, data):
        result = (self.dbrowToObject(obj, *row) for row in data)
        if self.sequencetype: result = self.sequencetype(result)
        return result
    
    def _getTable(self):
        if self.table: return self.table
        try:
            return self.targetclass.__table__
        except AttributeError:
            return self.cls.__table__
    
    def getCardinality(self):
        if self.sequencetype is None:
            return types.GeneratorType
        return self.sequencetype

def DBProperties(n):
    """Shortcut to create n DBProperty objects
    (for assigning to a,b = DBProperties(2))""" 
    return [DBProperty() for dummy in range(n)]
    
def _sqlWhere(fields, ids):
    if type(fields) in (str, unicode):
        fields, ids = [fields], [ids]
    return "(%s)" % " and ".join("(%s = %s)" % (field, dbtoolkit.quotesql(id))
                                 for (field, id) in zip(fields, ids))

def _select(columns, cachables, table):
    if isinstance(cachables, Cachable): cachables = (cachables,)
    if isinstance(columns, basestring): columns = (columns,)
    prototype = cachables[0]
    select = ", ".join(map(prototype.db.escapeFieldName, columns))
    
    reffield = prototype.__idcolumn__
    if type(reffield) in (str, unicode):
        if type(prototype.id) <> int:
            raise TypeError("Singular reffield with non-int id! Reffield: %r, cachable: %r, id: %r" % (reffield, prototype, prototype.id))
        where  = prototype.db.intSelectionSQL(reffield, (x.id for x in cachables))
    else:
        where = "((%s))" % ") or (".join(_sqlWhere(reffield, x.id) for x in cachables)
    SQL = "SELECT %s FROM %s WHERE %s" % (select, table, where)
    return prototype.db.doQuery(SQL)
