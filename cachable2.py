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

import idlabel
import amcatmemcache as store

class Cachable(idlabel.IDLabel):
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
        idlabel.IDLabel.__init__(self, id, None)

    @classmethod
    def _asProperty(cls, p, propname):
        """initialise and return p if it is a property, otherwise return None"""
        if isinstance(p,Property):
            if not p._initialised: p._initialise(cls, propname)
            return p
    @classmethod
    def getProperty(cls, attr):
       """return a Property attr if there is one, None otherwise"""
       try:
           p = getattr(cls, attr)
       except AttributeError:
           return
       return cls._asProperty(p, attr)
    
    def __getattribute__(self, attr):
        """if attr is a property, use its .get method. Otherwise, call super"""
        superfunc = super(Cachable, self).__getattribute__
        p = superfunc(attr)
        cls = superfunc("__class__")
        return p.get(self) if cls._asProperty(p, attr) else p
    

    def __setattr__(self, attr, value):
        """If attr is a property, cache the value. Otherwise, call super"""
        p = self.getProperty(attr)
        if p:
            p.cache(self, value) 
        else:
            super(Cachable, self).__setattr__(attr, value)

    def __delattr__(self, attr):
        """If attr is a property, uncache the value. Otherwise, call super"""
        p = self.getProperty(attr)
        if p:
            p.uncache(self) 
        else:
            super(Cachable, self).__delattr__(attr)

    def getType(self, property):
        """Get the type of the given property (or property name)"""
        if not isinstance(property, Property):
            property = self.getProperty(property)
        return property.getType(self)


            
class UnknownTypeException(Exception):
    def __init__(self, prop):
        Exception.__init__(self, "The type of property %s cannot be determined" % prop)

class Property(object):
    """Abstract base class of all Properties. 

    Subclasses should implement retrieve(obj)
    """
    def __init__(self):
        self._initialised = False
        self.observedType = None
    def _initialise(self, cls, propname):
        self.cls = cls
        self.propname = propname
        self.store = store.CachablePropertyStore(cls, propname)

    def get(self, obj):
        """Get obj from cache, or L{retrieve} and L{cache} it"""
        try:
            v = self.getCached(obj)
        except store.UnknownKeyException:
            v = self.retrieve(obj)
            self.cache(obj, v)
        if self.observedType is None: self.observedType = type(v)
        return v

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
        """Get the value for this property from the underlying store
        
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
        
class DBProperty(Property):
    """Property that retrieves its value from the database"""
    
    def retrieve(self, obj):
        """Use the database to retrieve the value of this property for obj"""
        data = _select(self.propname, obj)
        result = data[0][0]
        return result
    
    def getType(self, obj_or_db=None):
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

        


def _sqlWhere(fields, ids):
    if type(fields) in (str, unicode):
        fields, ids = [fields], [ids]
    return "(%s)" % " and ".join("(%s = %s)" % (field, dbtoolkit.quotesql(id))
                                 for (field, id) in zip(fields, ids))

def _select(columns, cachables):
    if isinstance(cachables, Cachable): cachables = (cachables,)
    if isinstance(columns, basestring): columns = (columns,)
    prototype = cachables[0]
    select = ", ".join(map(prototype.db.escapeFieldName, columns))
    table = prototype.__table__
    
    reffield = prototype.__idcolumn__
    if type(reffield) in (str, unicode):
        if type(prototype.id) <> int:
            raise TypeError("Singular reffield with non-int id! Reffield: %r, cachable: %r, id: %r" % (reffield, c, c.id))
        where  = prototype.db.intSelectionSQL(reffield, (x.id for x in cachables))
    else:
        where = "((%s))" % ") or (".join(sqlWhere(reffield, x.id) for x in cachables)
    SQL = "SELECT %s FROM %s WHERE %s" % (select, table, where) 
    return prototype.db.doQuery(SQL)
