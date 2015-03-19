# ##########################################################################
# (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
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

import logging

log = logging.getLogger(__name__)
from functools import wraps, partial

from django.conf import settings

SIMPLE_CACHE_SECONDS = getattr(settings, 'SIMPLE_CACHE_SECONDS', 2592000)


###########################################################################
#                       M E T H O D   C A C H I N G                       #
###########################################################################

CACHE_PREFIX = "_amcat_tools_caching_cache_"


def cached(func, cache_attr=CACHE_PREFIX):
    """Memoise the output of func

    @type func: method without parameters
    @param cache_attr: if given, use this key as object attribute to store the cache on
    """

    @wraps(func)
    def inner(self):
        """Decorator inner function: Return the cached value or execute func and cache results"""
        cache = _get_cache(self, cache_attr)
        try:
            return cache[func.__name__]
        except KeyError:
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


def get_object(model, pk, create_if_needed=True, pkname='pk'):
    """Create the model object with the given pk, possibly retrieving it
    from cache"""
    cache = _get_object_cache(model)
    try:
        return cache[pk]
    except KeyError:
        if create_if_needed:
            cache[pk] = model.objects.get(**{pkname: pk})
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
    setattr(_object_cache, key, {})


###########################################################################
#                  D J A N G O  M O D E L  C A C H I N G                  #
###########################################################################
def _get_cache_key(model, id):
    return ('%s:%s' % (model._meta.db_table, id)).replace(' ', '')

