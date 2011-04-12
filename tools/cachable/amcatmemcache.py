"""
Module to interface between cachable and memcache

memcache is a set of key/value pairs. For cachable:
- a key is a classname, a property name, and an int or tuple of ints
- a value is a primitive, a tuple of primitives, or a list of the same

For the moment, this module simply uses built-in memcache for storing and
retrieving. Later, a more efficient method can be swapped in that can do
better serialisation using these constraints and the binary protocol

Keys are stored as class_property(_key)+, where key is a hexadecimal number
Values are offered as (lists of (tuples of)) primitives, which memcache
  will pickle and zip

Command line usage to inspect/manipulate keystore:

python amcatmemcache.py ACTION CLASSNAME PROPNAME KEY
  ACTION: one of {get, delete}
  CLASSNAME: the name of the class (e.g. Project)
  PROPNAME: the name of the property (e.g. headline)
  KEY: the python string representation of the key (282 or 282,12)
"""

import pylibmc as memcache
#import memcache
import types
import logging; LOG = logging.getLogger(__name__)

#from amcat.tools.logging import amcatlogging; amcatlogging.debugModule()

class UnknownKeyException(EnvironmentError):
    pass

_CONNECTION = None
def _getConnection():
    global _CONNECTION
    if _CONNECTION is None:
        _CONNECTION = _connect()
    return _CONNECTION
def _connect():
    return memcache.Client(["127.0.0.1:11211"], binary=False)

def _serialise(obj):
    if type(obj) == unicode:
        return str(obj)
    if type(obj) == str:
        return obj
    if type(obj) != types.IntType:
        try:
            return obj.isoformat()
        except AttributeError:
            return "%s-%s-%s" % (obj.year, obj.month, obj.day)
    return obj

def key2bytes(klass, prop, key):
    """Return a byte-encoding of the key"""
    # memcached requires key chars > 33 and != 127, so use str(.) for now
    if type(klass) != str: klass = klass.__name__
    if type(key) == int: key = (key,)
    if not isinstance(key, (str, unicode)): 
        key = "_".join("%s" % _serialise(k) for k in key)
    return "%s_%s_%s" % (klass, prop, key)

def _debug(action, klass, prop, key, data=None):
    keybytes = key2bytes(klass, prop, key)
    if type(klass) != str: klass = klass.__name__
    LOG.debug("%s %s(%r).%s (%r) %s" % (action, klass, key, prop, keybytes, data or ""))
    

def get(klass, prop, key, conn=None):
    """Get the value corresponding to key

    If the key is unknown, raise a UnknownKey exception
    
    @param klass: a class
    @param prop: a property name
    @param key: a valid cachable key (int or int-tuple)
    @param conn: an optional connection object
    @return: a cachable value (primitive, tuple-of-primitive,
      or generator of (tuple-of) primitive
    """
    keybytes = key2bytes(klass, prop, key)
    #_debug("GET", klass, prop, key)
    val =_getConnection().get(keybytes)
    #_debug("GET", klass, prop, key, "-> %r" % (val,))
    if val is None:
        raise UnknownKeyException(keybytes)
    return val

def put(klass, prop, key, value, conn=None):
    """Set the value for the given key
    
    @param klass: a class
    @param prop: a property name
    @param key: a valid cachable key (int or int-tuple)
    @param value: a cachable value (primitive, tuple-of-primitive,
      or sequence of (tuple-of) primitive
    @param conn: an optional connection object
    """
    #LOG.debug(key)
    keybytes = key2bytes(klass, prop, key)
    #_debug("PUT", klass, prop, key, "<- %r" % (value,))
    _getConnection().set(keybytes, value)

def delete(klass, prop, key, conn=None):
    """Delete the value for the given key"""
    keybytes = key2bytes(klass, prop, key)
    #_debug("DEL", klass, prop, key)
    _getConnection().delete(keybytes)
    
class CachablePropertyStore(object):
    def __init__(self, klass, prop):
        self.klass = klass
        self.prop = prop
        self.conn = _getConnection()
    def get(self, key):
        return get(self.klass, self.prop, key, conn=self.conn)
    def set(self, key, value):
        return put(self.klass, self.prop, key, value, conn=self.conn)
    def delete(self, key):
        delete(self.klass, self.prop, key, conn=self.conn)
        

if __name__ == '__main__':
    import amcatlogging; log = amcatlogging.setup()

    import sys
    if len(sys.argv) < 4:
        print >>sys.stderr, __doc__
        sys.exit()
    action, klass, prop, key = sys.argv[1:5]
    key = eval(key)
    
    if action == "get":
        try:
            v = `get(klass, prop, key)`
        except UnknownKeyException:
            v = "None (key not in store)"
        print "GET %s(%r).%s value: %s" % (klass, key, prop, v)
    
    
