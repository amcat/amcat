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
Base class for Properties to be used with cachable
"""

from __future__ import unicode_literals, print_function, absolute_import
import logging; log = logging.getLogger(__name__)
from amcat.tools.cachable import amcatmemcache as store
from amcat.tools.cachable.cachable import Cachable
from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()

class Property(object):
    """Abstract base class of all Properties. 

    Subclasses should implement retrieve(obj)
    """
    
    def __init__(self, deprecated=False):
        self._initialised = False
        self._observedType = None
        self._deprecated = deprecated
        self._nullable = None
        
    def _initialise(self, cls, propname):
        """initialise this property with the given class and propname

        Properties are initialised for two reasons:
        - to 'bind' it to class and propname (which are not accessible on creation)
        - to allow resolving types that would cause import problems on creation
        """
        if self._initialised: return
        self.cls = cls
        self.propname = propname
        self._store = store.CachablePropertyStore(cls, propname)
        self._initialised = True

    def get(self, obj):
        """Get obj from cache, or L{retrieve} and L{cache} it

        Will call L{dataToObjects} to deserialise the value"""
        if self._deprecated:
            warnings.warn(DeprecationWarning("Property %s has been deprecated" % self))
        # if the objects dict contains this property, return it
        #TODO try to re-enable if self.propname in obj.__dict__: return obj.__dict__[self.propname]
        try:
            v = self.getCached(obj)
            #log.debug("Got cached %r.%s = %r" % (obj, self, v))
        except:
            #log.debug("%r.%s Not found in cache, retrieving from source" % (obj, self))
            v = self.retrieve(obj)
            #log.debug("Retrieved %r.%s = %r, caching" % (obj, self, v))
            self.cache(obj, v, isData=True)
        v = self.dataToObjects(obj, v)
        #log.debug("Converted into {0}".format(v))
        # remember the type info for later use
        if self._observedType is None: self._observedType = type(v)
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
            #log.debug("Setting %r.__dict__[%s] <- %r" % (obj, self.propname, value))
            # TODO Try to re-enable obj.__dict__[self.propname] = value
            value =  self.objectsToData(obj, value)
        self._store.set(obj._id, value)
    def uncache(self, obj):
        """Uncache this property for the given object"""
        #TODO type to re-enable if self.propname in obj.__dict__: del obj.__dict__[self.propname]
        self._store.delete(obj._id)
    def getCached(self, obj): 
        """Get the cached data value for obj, or raise an UnknownKeyException"""
        return self._store.get(obj._id)

    def retrieve(self, obj): 
        """Get the data value for this property from the underlying data source
        
        B{Abstract: Subclasses should override} 
        """
        raise NotImplementedError()
    def _update(self, db, obj, val):
        """Update the value on this property in the underlying store (eg database)

        This base implementation (only) calls L{cache} to update the cache.
        Note: Internal method: call L{Cachable.update} rather than
          this method to allow alternative update strategies (eg via
          stored procedure, single compound updates etc.)
        """
        self.cache(obj, val)
        
    def isNullable(self, db):
        """Returns whether a property-field is required or not."""
        return True

    def getType(self, obj=None):
        """Get the data type of this property

        @param obj: an optional Cachable object
          that can be used to help determine the type
        @return a type object  
        """
        #print "%s.getType(obj=%r); observedType=%r" % (self, obj, self.observedType)
        if (self._observedType is None
            and isinstance(obj, Cachable)):
            #try to get cached value
            #TODO: the logic of the try/except below is not very clear!
            try:
                val = self.getCached(obj)
                val = self.get(obj)
                self._observedType = type(val)
            except:
                pass
        if self._observedType is None:
            raise UnknownTypeException(self)
        return self._observedType        
                
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

    __repr__ = __str__
	
    ################### Caching ###################

    def prepareCache(self, cacher):
        """Optionally declare to cacher what to retrieve

        Preparation for a cacheMultiple operation. In this step, the property asks
        the cacher to retrieve certain information. The cachers does this and then calls
        doCache to actually set the cache for the retrieved values.

        @param cacher: A Cacher object that will do the caching
        """
        pass

    def doCache(self, cacher, obj=None):
        """Optionally cache the values from the cacher (see L{prepareCache})"""
        pass

    def cachePerObject(self, db, objects):
	"""Optionally cache the values for these objects"""
	pass
    

      
        
class UnknownTypeException(Exception):
    def __init__(self, prop):
        Exception.__init__(self, "The type of property %s cannot be determined" % prop)


