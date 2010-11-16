
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
import logging; log = logging.getLogger(__name__)


class Meta(type):
    """Metaclass to  ensure properties are initialised"""
    def __getattribute__(cls, attr):
        """Get a class attribute, and _initialise it if possible/needed"""
        result = type.__getattribute__(cls, attr)
        try: result._initialise(cls, attr)
        except AttributeError: pass # only initialise properies
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

    ############### Internal Property access  #########################
        
    @classmethod
    def _getProperty(cls, attr):
       """return a Property attr if there is one, TypeError (or AttributeError) otherwise"""
       p = getattr(cls, attr)
       if isinstance(p, Property):
           return p
       raise TypeError("%s is not a Property" % attr)
   
    @classmethod
    def _getProperties(cls, deprecated=True):
        """Return all DBPropterties and Foreignkeys
        
        @type deprecated: Boolean
        @param deprecated: If true, return deprecated functions also
        
        @return: sequence of 2-tuple with the name of the property and the
        property itself"""
        for name in dir(cls):
            prop = getattr(cls, name)
            if isinstance(prop, Property):
                if deprecated or not prop.deprecated:
                    yield (name, prop)
                    
    ############ Public Attribute Access (operator overloading)  ######################
    
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
            
    ############### Cache inspection and manipulation ############

    def uncache(self):
        """Remove all cached entries for this object"""
        for name, prop in self._getProperties():
            prop.uncache(self)

    ############### Inspection  #########################
            
    def getType(self, prop):
        """Get the type of the given property (or property name)"""
        if not isinstance(prop, Property):
            prop = self._getProperty(prop)
        return prop.getType(self)

    ############### IDLabel implementation  #########################
    
    @property
    def label(self):
        # if a __labelprop__ is defined, return that, otherwise, call super
        try:
            return getattr(self, self.__labelprop__)
        except AttributeError:
            return super(Cachable, self).label

    ############### Manipulating Cachables  #########################
        
    def update(self, db, **props):
        """Update the database db with the given props

        Note that the caller is responsible for maintaining the db transaction
        (i.e. for committing after an update).

        Default implementation calls _updateProperty(db, prop, val) for each prop, val in props,
        which will call prop._update(db, self, val). Subclasses may override this function and/or
        the underlying _updateProperty to implement updating via e.g. stored procedures. If overridden,
        subclass is responsible for making sure the cache store is invalidated/updated where appropriate.
        """
        for propname, val in props.iteritems():
            prop = self._getProperty(propname)
            self._updateProperty(db, prop, val)

    def _updateProperty(self, db, prop, val):
        """Update a single property by calling prop._update. See L{update}"""
        prop._update(db, self, val)


    ############### DB Specific (class)methods #########################    

    def delete(self, db):
        """Delete this Cachable object, and uncache all properties"""
        db.delete(self.__table__, self._getWhere())
        self.uncache()
        
    @classmethod
    def create(cls, db, idvalues=None, **props):
        """Create a new instance of this Cachable class, initialised with props

        Note that the caller is responsible for maintaining the db transaction
        (i.e. for committing after an update).

        Default implementation calls a db.insert with the given props, and creates
        the Cachable object with the returned id. The props are then cached.
        """
        if idvalues is not None:
            idcol = cls.__idcolumn__
            if type(idcol) not in (list, tuple):
                idcol, idvalues = [idcol], [idvalues]
            allprops = dict(props.items() + zip(idcol, idvalues))
            db.insert(cls.__table__, allprops, retrieveIdent=False)
        else:
            idvalues= db.insert(cls.__table__, props)
        result = cls(db, idvalues)
        log.debug("Created object %r" % result)
        for propname, val in props.iteritems():
            prop = result._getProperty(propname)
            log.debug("Caching %s.%s <- %s" % (result, propname, val))
            prop.cache(result, val)
        return result
    
    @classmethod
    def getAll(cls, db):
        """Get all known objects of this type"""
        if type(cls.__idcolumn__) in (str, unicode):
            rowfunc = lambda i : cls(db, i)
        else: #need to pass arg tuple as single id argument to constructor
            rowfunc = lambda *i : cls(db, i)                      
        return db.select(cls.__table__, cls.__idcolumn__, rowfunc=rowfunc)

    def _getWhere(self):
        idcol, oid = self.__idcolumn__, self.id
        if type(idcol) in (str, unicode):
            if type(oid) != int: raise ValueError("Non-integral id on object %r with scalar idcolumn %r!" % (obj, idcol)) 
            return {idcol : oid}
        else:
            if type(oid) != tuple: raise ValueError("Scalar id on object %r with tuple idcolumn %r!" % (obj, idcol)) 
            return dict(zip(idcol, oid)) 
    
            
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
        if self._initialised: return
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
            log.debug("Got cached %r.%s = %r" % (obj, self, v))
        except store.UnknownKeyException:
            log.debug("%r.%s Not found in cache, retrieving from source" % (obj, self))
            v = self.retrieve(obj)
            log.debug("Retrieved %r.%s = %r, caching" % (obj, self, v))
            self.cache(obj, v, isData=True)
        v = self.dataToObjects(obj, v)
        log.debug("Converted into %r" % v)
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

    def objectsToData(self, obj, objects):
        """Serialise the given object(s) into data

        This should be the inverse of L{dataToObjects}
        
        @param obj: the 'parent' object of the objects
        @param objects: the object(s) to serialise
        @return: the raw data that can be stored (eg in memcache)
        """
        return objects
        
    
    def cache(self, obj, value, isData=False):
        """Cache the given object or data value for this property

        @param obj: the object whose property to cache
        @param value: the value to cache
        @param isData: unless True, serialise the value before caching
        """
        if not isData:
            value =  self.objectsToData(obj, value)
        self.store.set(obj.id, value)
    def uncache(self, obj):
        """Uncache this property for the given object"""
        self.store.delete(obj.id)
    def getCached(self, obj): 
        """Get the cached data value for obj, or raise an UnknownKeyException"""
        return self.store.get(obj.id)

    def retrieve(self, obj): 
        """Get the data value for this property from the underlying data source
        
        B{Abstract: Subclasses should override} 
        """
        abstract
    def _update(self, db, obj, val):
        """Update the value on this property in the underlying store (eg database)

        This base implementation (only) calls L{cache} to update the cache.
        Note: Internal method: call L{Cachable.update} rather than
          this method to allow alternative update strategies (eg via
          stored procedure, single compound updates etc.)
        """
        self.cache(obj, val)

    def getType(self, obj=None):
        """Get the data type of this property

        @param obj: an optional Cachable object
          that can be used to help determine the type
        @return a type object  
        """
        #print "%s.getType(obj=%r); observedType=%r" % (self, obj, self.observedType)
        if (self.observedType is None
            and isinstance(obj, Cachable)):
            #try to get cached value
            #TODO: the logic of the try/except below is not very clear!
            try:
                val = self.getCached(obj)
                val = self.get(obj)
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
        if self._initialised: return
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

    def objectToDbrow(self, obj, *dbvalues):
        """Convert an amcat object to a db row
        
        @param obj: the "parent object" of the new object
        @param object: a single 'domain' object
        @return dbvalues: the row tuple as it was returned from the db
        """
        if isinstance(obj, idlabel.IDLabel):
            obj = obj.id
        if type(obj) not in (list, tuple): obj = (obj, )
        return obj

    def objectsToData(self, obj, objects):
        log.debug("Serialising %s=%r" % (self, objects))
        return [self.objectToDbrow(objects)]
        
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
        """
        return obj.db.select(self._getTable(), self._getColumns(), obj._getWhere(), alwaysReturnTable=True)
    
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

    def _update(self, db, obj, val):
        """Create and execute an SQL UPDATE statement to update the db"""
        #TODO: use serialisation method
        log.debug("UPDATEing %r.%s -> %r" % (obj, self, val))
        if isinstance(val, idlabel.IDLabel): val = val.id
        cols = self._getColumns()
        if type(cols) in (str, unicode):
            update = {cols : val}
            val = (val,) # for caching
        else:
            update = dict(zip(cols, val))
        obj.db.update(self._getTable(), update, obj._getWhere())
        self.cache(obj, [val])
            
        
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

    def objectsToData(self, obj, objects):
        log.debug("FKSerialising %s=%r" % (self, objects))
        return [self.objectToDbrow(o) for o in objects]
    
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
        child = self.targetclass.create(db, idvalues=idvalues, **props)
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
    
def DBProperties(n):
    """Shortcut to create n DBProperty objects
    (for assigning to a,b = DBProperties(2))""" 
    return [DBProperty() for dummy in range(n)]

def cacheMultiple(*args, **kargs): pass

class UnknownTypeException(Exception):
    def __init__(self, prop):
        Exception.__init__(self, "The type of property %s cannot be determined" % prop)



#import amcatlogging; amcatlogging.debugModule()
