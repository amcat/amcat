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
"""

import memcache

class UnknownKeyException(EnvironmentError):
    pass

_CONNECTION = None
def _getConnection():
    global _CONNECTION
    if _CONNECTION is None:
        _CONNECTION = _connect()
    return _CONNECTION
def _connect():
    return memcache.Client(["127.0.0.1:11211"])

def key2bytes(klass, prop, key):
    """Return a byte-encoding of the key"""
    # memcached requires key chars > 33 and != 127, so use str(.) for now
    if type(key) == int: key = (key,)
    return "%s_%s_%s" % (klass.__name__, prop,
                         "_".join("%x" % k for k in key))

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
    #print "GETTING %r" % keybytes
    val =_getConnection().get(keybytes)
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
    keybytes = key2bytes(klass, prop, key)
    #print "SETTING %r" % keybytes
    _getConnection().set(keybytes, value)

def delete(klass, prop, key, conn=None):
    """Delete the value for the given key"""
    keybytes = key2bytes(klass, prop, key)
    #print "DELETING %r" % keybytes
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
        
