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
Decorators and functions for caching properties

@cached on a property or methods without arguments will memoise a cached
value on the object

@invalidates will clear the cache for this object for all cached functions

Use reset and set_cache to manually clear and set the cache
"""

from __future__ import unicode_literals, print_function, absolute_import


import logging; log = logging.getLogger(__name__)
from functools import wraps, partial


###########################################################################
#                       M E T H O D   C A C H I N G                       #
###########################################################################

CACHE_PREFIX = "_amcat_tools_caching_cache_"

def cached(func, cache_attr=CACHE_PREFIX):
    """Memoise the output of func

    @type func: method without parameters
    @param key: if given, use this key as object attribute to store the cache on
    """
    @wraps(func)
    def inner(self):
        """Decorator inner function: Return the cached value or execute func and cache results"""
        cache = _get_cache(self, cache_attr)
        try:
            #log.debug("Querying cache %r.%s" % (self, cache_attr))
            return cache[func.__name__]
        except KeyError:
            log.info("Not found, setting cache for %r.%s" % (self, cache_attr))
            return _set_cache_value(cache, func.__name__, func(self))
    return inner

def cached_named(cache_attr):
    """Creates a cached decorator with a different cache attribute"""
    return partial(cached, cache_attr=CACHE_PREFIX + cache_attr)

def invalidates(func, cache_attr=CACHE_PREFIX):
    """Invalidate the cache before the func is run"""
    @wraps(func)
    def inner(self, *args, **kargs):
        """Decorator inner function: reset the cache and run func as normal"""
        f = func(self, *args, **kargs)
        _reset(self, cache_attr)
        return f
    return inner

def invalidates_named(cache_attr):
    """Creates a cached invalidator with a different cache attribute"""
    return partial(invalidates, cache_attr=CACHE_PREFIX + cache_attr)

def _reset(obj, cache_attr):
    """Reset the cache on the object in this value"""
    log.info("Resetting %r.%s" % (obj, cache_attr))

    setattr(obj, cache_attr, {})

def reset(obj, cache_attr=""):
    """Reset the cache on the given object"""
    _reset(obj, CACHE_PREFIX + cache_attr)

def _get_cache(obj, cache_attr=CACHE_PREFIX):
    """Get or create the cache dictionary on obj"""
    try:
        return getattr(obj, cache_attr)
    except AttributeError:
        setattr(obj, cache_attr, {})
        return getattr(obj, cache_attr)

def _set_cache_value(cache, name, value):
    """Set the cache to value for the func, returning value"""
    cache[name] = value
    return value
    
def set_cache(obj, name, value, cache_attr=""):
    """Set the value as the cached value for func"""
    _set_cache_value(_get_cache(obj, CACHE_PREFIX + cache_attr), name, value)
    



###########################################################################
#                       O B J E C T   C A C H I N G                       #
###########################################################################

# Setup thread-local cache for codebooks
import threading
_object_cache = threading.local()

def _get_object_cache(model):
    key = CACHE_PREFIX + model.__name__
    try:
        return getattr(_object_cache, key)
    except AttributeError:
        cache = {}
        setattr(_object_cache, key, cache)
        return cache

def get_object(model, pk, create_if_needed=True):
    """Create the model object with the given pk, possibly retrieving it
    from cache"""
    cache = _get_object_cache(model)
    try:
        return cache[pk]
    except KeyError:
        if create_if_needed:
            cache[pk] = model.objects.get(pk=pk)
            return cache[pk]


def get_objects(model, pks):
    """
    Get or create the model objects, using one query for all creates
    Does not preserve the order of objects in pks!
    """
    todo = set()
    for pk in pks:
        obj = get_object(model, pk, create_if_needed=False)
        if obj is None:
            todo.add(pk)
        else:
            yield obj
    if not todo: return
    cache = _get_object_cache(model)
    for obj in model.objects.filter(pk__in=todo):
        cache[obj.id] = obj
        yield obj
    
def clear_cache(model):
    """Clear the local codebook cache manually, ie in between test runs"""
    key = CACHE_PREFIX + model.__name__
    setattr(_object_cache, key , {})

    
    
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCaching(amcattest.PolicyTestCase):

    class TestClass(object):
        """Class for testing ('docstrings, omdat het moet (van pylint)') """
        def __init__(self, x=1, y=2):
            self.changed = False
            self.x = x
            self.y = y
        @property
        @cached
        def xprop(self):
            """Cached property"""
            self.changed = True
            return self.x
        @invalidates
        def set_x(self, x):
            """Invalidating setter"""
            self.x = x
            return x
        @cached_named("y_cache")
        def get_y(self):
            """Func for testing named cache"""
            self.changed = True
            return self.y
        @invalidates_named("y_cache")
        def set_y(self, y):
            """Func for testing invalidate named cache"""
            self.y = y
    
    def test_cached(self):
        """Does caching work"""
        t = TestCaching.TestClass(x=4)
        self.assertEqual(t.xprop, 4)
        self.assertTrue(t.changed)
        t.changed = False
        self.assertEqual(t.xprop, 4)
        self.assertFalse(t.changed)
        t.x = 7 # manual change, does not invalidate cache
        self.assertEqual(t.xprop, 4)
        self.assertFalse(t.changed)

    def test_invalidate(self):
        """Does invalidate work properly"""
        t = TestCaching.TestClass(x=4)
        self.assertEqual(t.xprop, 4)
        t.changed = False
        x = t.set_x(12)
        self.assertEqual(x, 12, "Cached method does not return value")
        self.assertEqual(t.xprop, 12)
        self.assertTrue(t.changed)

    def test_reset(self):
        """Does manual reset work properly"""
        t = TestCaching.TestClass(x=4)
        self.assertEqual(t.xprop, 4)
        t.changed = False
        t.x = 17
        self.assertEqual(t.xprop, 4)
        self.assertFalse(t.changed)
        reset(t)
        self.assertEqual(t.xprop, 17)
        self.assertTrue(t.changed)
        
        
    def test_named(self):
        """Do named caches work?"""
        t = TestCaching.TestClass(x=4)
        y = t.get_y()

        # Setting the x prop should _not_ invalidate the cache for y
        t.changed = False
        t.set_x(17)
        self.assertEqual(y, t.get_y())
        self.assertFalse(t.changed)

        # Setting the y prop should _not_ invalidate the cache for x
        x = t.xprop
        t.changed = False
        t.set_y(1)
        self.assertEqual(x, t.xprop)
        self.assertFalse(t.changed)
        
        # ... but it should invalidate the cache for y        
        self.assertEqual(t.get_y(), 1)
        self.assertTrue(t.changed)

        # ... and so should calling named reset
        t.changed = False
        t.y = 9
        reset(t, "y_cache")
        self.assertEqual(x, t.xprop)
        self.assertFalse(t.changed)
        self.assertEqual(t.get_y(), 9)
        self.assertTrue(t.changed)

        
        
    def test_set_cache(self):
        """Can we manually set the cache?"""
        t = TestCaching.TestClass(x=4, y=1)

        # Are set values used?
        set_cache(t, "xprop", 99)
        self.assertEqual(t.xprop, 99)
        self.assertFalse(t.changed)
        # Does reset bring back real value?
        reset(t)
        self.assertEqual(t.xprop, 4)
        self.assertTrue(t.changed)

        # Same for named prop
        t.changed = False
        set_cache(t, t.get_y.__name__, 7, "y_cache")
        self.assertEqual(t.get_y(), 7)
        self.assertFalse(t.changed)
        reset(t, "y_cache")
        self.assertEqual(t.get_y(), 1)
        self.assertTrue(t.changed)

    def test_object_cache(self):
        from amcat.models.project import Project
        pid = amcattest.create_test_project().id
        with self.checkMaxQueries(1, "Get project"):
            p = get_object(Project, pid)
        with self.checkMaxQueries(1, "Get cached project"):
            p2 = get_object(Project, pid)
        self.assertIs(p, p2)

        clear_cache(Project)
        with self.checkMaxQueries(1, "Get cleared project"):
            p3 = get_object(Project, pid)
        self.assertIsNot(p, p3)
        self.assertEqual(p, p3)
        
    def test_get_objects(self):
        from amcat.models.project import Project
        pids = [amcattest.create_test_project().id for _x in range(10)]
        
        with self.checkMaxQueries(1, "Get multiple projects"):
            ps = list(get_objects(Project, pids))
        
        with self.checkMaxQueries(0, "Get multiple cached projects"):
            ps = list(get_objects(Project, pids))
        
        with self.checkMaxQueries(0, "Get multiple cached projects one by one"):
            ps = [get_objects(Project, pid) for pid in pids]
        
#from amcat.tools import amcatlogging; amcatlogging.infoModule()
