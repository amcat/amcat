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

from __future__ import unicode_literals, print_function, absolute_import


import logging; log = logging.getLogger(__name__)
# logs manually commented out because they *really* slow things down

from amcat.tools import idlabel, toolkit

from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()

#import amcatlogging; amcatlogging.infoModule()

class Meta(type):
    """Metaclass to  ensure properties are initialised"""
    def __getattribute__(cls, attr):
        """Get a class attribute, and _initialise it if possible/needed"""
        result = type.__getattribute__(cls, attr)
        if isinstance(result, Property):
            initialiser = result._initialise(cls, attr)
        return result


class Cachable(idlabel._Identity):
    """Main class of the Cachable structure
    
    A Cachable class has class-level properties that are 
    connected to a backing store from which they get/set 
    (class_property_id):value pairs

    Cachable works by overriding the __getattribute__, __setattr__,
    and __delattr__ methods. These methods now check whether the
    attribute is a property, and if so call get/set/del on the property    
    """

    __metaclass__ = Meta
    __slots__ = ('db', '_id',)
    
    def __init__(self, db, *id):
        """Create a cachable with db and id
        @param db: database connection
        @param id: the id of this object
        """
        if len(id) <> len(self._getIDColumns()):
            raise Exception("Error on creating %s instance: ID %r and idcol %r do not match" % (self.__class__, id, self._getIDColumns()))
        self.db = db
        self._id = id

    def _identity(self):
        return (self.__class__ , self._id)

    @property
    def id(self):
        if len(self._id) == 1: return self._id[0]
        return self._id

    @classmethod
    def _getIDColumns(cls):
        return _ensureTuple(cls.__idcolumn__)
    
    ############### Internal Property access  #########################

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
        if "_" not in attr and attr not in self.__slots__:
            p = getattr(self.__class__, attr)
            if isinstance(p, Property):
                result = p.get(self)
                return result
        return super(Cachable, self).__getattribute__(attr)


    def __setattr__(self, attr, value):
        """If attr is a property, cache the value. Otherwise, call super"""
        
        p = getattr(self.__class__, attr)
        if isinstance(p, Property):
            p.cache(self, value)
        else:
            super(Cachable, self).__setattr__(attr, value)

    def __delattr__(self, attr):
        """If attr is a property, uncache the value. Otherwise, call super"""
        
        p = getattr(self.__class__, attr)
        if isinstance(p, Property):
            p.uncache(self)
        else:
            super(Cachable, self).__delattr__(attr)
            
    ############### Cache inspection and manipulation ############

    def uncache(self):
        """Remove all cached entries for this object"""
        for name, prop in self._getProperties():
            prop.uncache(self)

    ############### Inspection  #########################
            
    def getType(self, prop):
        """Get the type of the given property (or property name)"""
        if not isinstance(prop, Property):
            prop = getattr(self.__class__, prop)
        return prop.getType(self)
    
    def isNullable(cls, prop):
        """Checks if `prop` is a required field"""
        if not isinstance(prop, Property):
            prop = self._getProperty(prop)
        return prop._isNullable(self.db)

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
            prop = getattr(self.__class__, propname)
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
        """Create a new instance of this Cachable class, initialized with props

        Note that the caller is responsible for maintaining the db transaction
        (i.e. for committing after an update).

        Default implementation calls a db.insert with the given props, and creates
        the Cachable object with the returned id. The props are then cached.
        """
        
        data = {}
        for key, val in props.iteritems():
            prop = getattr(cls, key, None)
            if isinstance(prop, Property):
                cols = prop._getColumns()
                vals = prop.objectToDbrow(val)
                data.update(dict(toolkit.zipp(cols, vals)))
            else:
                data[key] = val
        if idvalues is not None:
            idcol = cls._getIDColumns()
            idvalues = [getattr(obj, "id", obj) for obj in _ensureTuple(idvalues)]
            data.update(dict(toolkit.zipp(idcol, idvalues)))
            db.insert(cls.__table__, data, retrieveIdent=False)
        else:
            idvalues= (db.insert(cls.__table__, data, retrieveIdent=cls.__idcolumn__),)
        result = cls(db, *idvalues)
        for propname, val in props.iteritems():
            prop = getattr(cls, key, None)
            if isinstance(prop, Property):
                prop.cache(result, val)
        return result
    
    @classmethod
    def _get_rowfunc(cls, db):
        if type(cls.__idcolumn__) in (str, unicode):
            return lambda i : cls(db, i)
        else: #need to pass arg tuple as single id argument to constructor
            return lambda *i : cls(db, i)
    
    @classmethod
    def all(cls, db):
        """Get all known objects of this type"""
        return db.select(cls.__table__, cls.__idcolumn__, rowfunc=cls._get_rowfunc(db))
    
    @classmethod
    def find(cls, db, **props):
        """Find objects with given properties
        
        @example: User.find(db, username='piet')
        @example: Function.find(db, office=Object(db, 123))
        
        This is also correct:
        @example: Function.find(db, office=123)
        """
        def getcols(attr):
            p = cls._getProperty(attr)
            if not p: raise TypeError("Cannot find property %s.%s" % (cls, key))
            return p._getColumns()
        
        def getvals(value):
            if isinstance(value, Cachable):
                return value.id
            return value
        
        def totuple(value):
            if type(value) in (tuple, list): return value
            return (value,)
        
        where = [(getcols(k), getvals(v)) for k,v in props.items()]
        where = [zip(totuple(k), totuple(v)) for k,v in where]
        where = dict([item for sublist in where for item in sublist]) # Flattening list
        
        return db.select(cls.__table__, cls.__idcolumn__, where=where, rowfunc=cls._get_rowfunc(db))
    
    @classmethod
    def get(cls, db, **props):
        """Same function as find, but raises an error when zero or more than one
        objects are found.
        
        @example: Politician.get(db, object=295)
        @example: Politician.get(db, Object(db, 295))"""
        obj = cls.find(db, **props)
        if len(obj) is 1: return obj[0]
        
        raise ValueError("Database returned zero or more than one objects")

    def _getWhere(self, refcolumns=None):
        if not refcolumns: refcolumns = self._getIDColumns()
        return dict(toolkit.zipp(refcolumns, self._id))

    def __unicode__(self):
        result = self.label
        if type(result) == str: return result.decode("latin-1")
        else: return unicode(result)
    def __str__(self):
        try:
            result = self.label
        except AttributeError:
            return self.__repr__()
        if type(result) == unicode: return result.encode("ascii","replace")
        else: return str(result)
    def __repr__(self):
        return "%s(%s)" % (self.__class__, self.id)
        return str(self)
    def idlabel(self):
        return "{0}: {1}".format(self.id, self.label)


def _ensureTuple(vals):
    """Ensure that vals is a tuple (ie convert scalar into 1-tuple)"""
    if vals is None: return vals
    if isinstance(vals, list):
        vals = tuple(vals)
    if not isinstance(vals, tuple):
        return (vals, )
    return vals

def _allowScalar(vals):
    """If vals is a 1-tuple, return a scalar"""
    if len(vals) == 1: return vals[0]
    return vals

def DBProperties(n):
    """Shortcut to create n DBProperty objects
    (for assigning to a,b = DBProperties(2))""" 
    return [DBProperty() for dummy in range(n)]

# import for easier access
from amcat.tools.cachable.property import Property, UnknownTypeException
from amcat.tools.cachable.dbproperty import DBProperty, ForeignKey



