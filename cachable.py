"""
Cachable contains a number of classes that function as the
'database' layer of AmCAT. A Cachable class is a class that
is linked to a database table, with an id and table name, and
has a number of properties corresponding (normally) to DB fields.

These properties can be accessed as regular python properties
(object.property), but behind the screens check the cache, and if
it is not found, retrieves the value from the database and caches it.
Properties also allow post-get hooks. Foreign Key properties function
as one-to-many relations. Properties are referenced only by the cachable
object, and contain the cached data themselves, so python garbage collection
removes all cached values on object destruction.

The CacheMeta metaclass caches the objects as well as the values using
pre-init caching on key (class, id) with weak references.

To avoid the cpu cost of creating many Properties on object creation,
PropertyFactories can be used as class attributes that will create
the Property at the moment it is needed.

(C) 2009-2010 Wouter van Atteveldt

    #TODO: - maybe use __dict__ instead of __properties__, and catch the
    # settattribute and getattribute to display the correct behaviour?
    # - allow caching by setting e.g. article.headline = "bla"
"""

import toolkit, collections, inspect
#from functools import partial
import weakref
        
_CACHE = {}
class CachingMeta(type):
    """
    Metaclass to allow Cachable instances to be cached themselves.
    If a class has this metaclass, instances
    will be cached by Class and ID.
    """
    def __call__(cls, db, *args, **kargs):
        if not args: #Call default creator
            return type.__call__(cls, db, *args, **kargs)
        id = args[0]
        if (cls, id) in _CACHE:
            # return cached instance, call weakref to see
            # whether it still exists
            obj = _CACHE[cls, id]()
            #print "FROM CACHE", cls, id
            if obj is not None: return obj
        # cache and return new instance
        #print "NOT FROM CACHE", `cls`, `id`
        obj = type.__call__(cls, db, *args, **kargs)
        _CACHE[cls, id] = weakref.ref(obj)
        return obj

class Cachable(toolkit.IDLabel):
    """
    Base class for all 'cachable' objects. Allows the registration of
    'properties' that will be accessible just like normal properties, but
    behind the screens will use the db to get their values and cache these
    values. See usage in the __name__==__main__ driver section
    """
    def __init__(self, db, id, **cache):
        """Create the Cachable with the given database and id
        Optionally, provide property=value pairs to cache immediately as **cache"""
        if id is None: raise TypeError("ID should not be None!")
        if db is None: raise TypeError("DB should not be None!")
        self.db = db
        self.id = id
        self.__properties__ = {}
        if cache:
            self.cacheValues(**cache)
        #for k,v in cache.iteritems():
        #    if k is not None:
        #        self.cacheValues(**{k:v})
        #sanity check on idcolumn/id
        if id and '__idcolumn__' in self.__class__.__dict__:
            if type(self.__idcolumn__) in (str, unicode) and type(id) <> int:
                raise TypeError("Type Mismatch between icolumn %r and id %r on object %r" %
                                (self.__idcolumn__, id, self.__class__.__name__))
        #else: print self.__class__.__name__

    def _getPropertyNames(self):
        for attr in self.__properties__: yield attr
        for name, factory in self._getPropertyFactories():
            if name not in self.__properties__:
                yield name 
    def _getProperty(self, attr):
        """Find the property attr, either in __properties__, or as a class attribute property factory"""
        prop = self.__properties__.get(attr)
        if prop is not None: return prop
        for name, factory in self._getPropertyFactories():
            if name == attr:
                prop = factory.createProperty(self, attr)
                self.__properties__[attr] = prop
                return prop
    def _getPropertyFactories(self):
        """Generate all property factories from class (and superclass) attributes"""
        for base in inspect.getmro(type(self)):  # get class properties of base classes as well
            for propname, factory in base.__dict__.iteritems():
                if isinstance(factory, PropertyFactory):
                    yield propname, factory
            for propname in base.__dict__.get("__dbproperties__", ()):
                yield propname, DBPropertyFactory(propname)

    def __getattribute__(self, attr):
        """Main magic: if attr is a property: return its .get().
        Otherwise, call superclass __getattribute__"""
        if  attr not in ("__properties__", "_getProperty", "_getPropertyFactories", "__dict__", "id"):
            prop = self._getProperty(attr)
            if prop:
                return prop.get()
        try:
            return toolkit.IDLabel.__getattribute__(self, attr) #superclass
        #return super(Cachable, self).__getattribute__(attr)
        except AttributeError, e:
            if attr <> "label": raise
            try:
                attr = self.__labelprop__
            except AttributeError:
                attr = "name"
            if attr:
                return self.__getattribute__(attr)
                
    def addDBProperty(self, property, fieldname=None, func=None, table=None):
        "Convenience function to add a DB Property"
        return self.addProperty(property, DBProperty(self, fieldname or property, func, table))
    def addFunctionProperty(self, property, func):
        "Convenience function to add a function Property"
        return self.addProperty(property, FunctionProperty(self, func))
    def addDBFKProperty(self, property, *args, **kargs):
        "Convenience function to add a DBFK Property"
        return self.addProperty(property, DBFKProperty(self, *args, **kargs))
    def addProperty(self, propname, prop):
        "Add the given property to the __properties__ dict"
        self.__properties__[propname] = prop
        return prop
    def cacheValues(self, **values):
        """Cache the property:value pairs given in **values"""
        for prop, val in values.iteritems():
            p = self._getProperty(prop)
            if not p: raise AttributeError("Cannot find property %s of %r" % (prop, self))
            p.cache(val)
    def cacheAllProperties(self):
        """Cache all properties"""
        cache([self], *tuple(self._getPropertyNames()))
    def removeCached(self, prop):
        """Remove the cached value from the given property"""
        self._getProperty(prop).uncache()
    def cacheProperties(self, *propnames):
        """Ask the given properties to get() their values and cache themselves"""
        cacheMultiple([self], propnames)
    def sqlFrom(self, table=None):
        return sqlFrom([self], table)

    
    def exists(self):
        """Checks whether the database contains a record for this object"""
        SQL = "select count(*) from %s where %s" % (self.__table__, sqlWhere(self.__idcolumn__, self.id))
        return bool(self.db.getValue(SQL))
    def deleteFromDB(self, commit=False):
        SQL = "delete from %s where %s" % (self.__table__, sqlWhere(self.__idcolumn__, self.id))
        self.db.doQuery(SQL)
        if commit: self.db.commit()
        


##################################
#         Properties             #
##################################
        
class Property(object):
    """
    Base class of all properties, subclasses
    should at least implement retrieve
    """
    def __init__(self, cachable):
        self.cachable = cachable
        self.value = None
        self.cached = False
    def get(self):
        if not self.cached:
            self.cache(self.retrieve())
        return self.value
    def cache(self, value):
        self.value = value
        self.cached = True
    def retrieve(self): abstract
    def prepareCache(self, cacher): pass
    def doCache(self, cacher): pass
    def uncache(self):
        self.value = None
        self.cached = False

class DBProperty(Property):
    """
    Property representing (normally) a column in the
    row defining an object.
    """
    def __init__(self, cachable, fieldname, func=None, table=None, objfunc=None, dbfunc=None, decode=False):
        """
        Fieldname is the name of the field to retrieve. It can be a
        tuple, in which case multiple values will be passed to the
        deserializer. The various func arguments allow deserializing
        using a function with only the results, a function with the
        cachable object, or a function with the database
        connection. The latter is especially useful for calling
        standard Cachable(db, id) constructors.
        """
        Property.__init__(self, cachable)
        self.fieldname = fieldname
        self.func = func
        self.objfunc = objfunc
        self.dbfunc = dbfunc
        self.table = table
        self.decode = decode
    def process(self, *values):
        # decode UTF, remove guard if all is ok
        import dbtoolkit
        if self.decode:
            if '__encodingprop__' in dir(self.cachable):
                encoding = self.cachable.__getattribute__(self.cachable.__encodingprop__)
            else:
                encoding = None
            values = tuple(dbtoolkit.decode(v, encoding) if type(v) == str else v
                           for v in values)
        if self.func: return self.func(*values)
        if self.objfunc: return self.objfunc(self.cachable, *values)
        if self.dbfunc: return self.dbfunc(self.cachable.db, *values)
        return values[0]
    def retrieve(self):
        if not self.cachable.db: raise Exception("Cachable object %r has no database connection" % self.cachable) 
        seq = type(self.fieldname) in (list, tuple)
        if seq:
            field = ",".join(map(quotefield, self.fieldname))
        else:
            field = quotefield(self.fieldname)
        SQL = "SELECT %s %s" % (field, self.cachable.sqlFrom(self.table))
        d = self.cachable.db.doQuery(SQL)
        if d: return self.process(*d[0])
    def prepareCache(self, cacher):
        if self.cached: return
        cacher.addDBField(self.fieldname, table=self.table)
    def doCache(self, cacher):
        if self.cached: return
        val = cacher.getDBData(self.cachable, self.fieldname, self.table)
        self.cache(self.process(val))

class FunctionProperty(Property):
    "Trivial implementation of retrieve using a supplied function"
    def __init__(self, cachable, func):
        Property.__init__(self, cachable)
        self.retrieve =  func


class Partial(object):
    def __init__(self, function, arg):
        self.function = function
        self.arg = arg
    def __call__(self, *args, **kargs):
        return self.function(self.arg, *args, **kargs)
        
class DBFKProperty(Property):
    """
    Property representing a one-to-many relation
    """
    def __init__(self, cachable, table, targetfields, reffield=None, function=None, endfunc = None, orderby=None, dbfunc=None, factory=None, uplink=None, objfunc=None, distinct=False, filter=None):
        """
        Table is the foreign key table, target fields the fields to retrieve.
        Reffield is the field to select on, defaulting to the idcolumn of the cachable.
        function (or dbfunc) are used on individual child objects
        endfunc (default: list) are used on the resulting sequence
        orderby can be a database field to ORDER BY
        """
        Property.__init__(self, cachable)
        self.table = table
        self.targetfields = targetfields
        if function:
            self.function = function
        elif dbfunc:
            self.function = Partial(dbfunc, self.cachable.db)
        elif objfunc:
            self.function = Partial(objfunc, self.cachable)
        elif factory:
            if uplink is None: uplink = type(cachable).__name__.lower()
            factory = factory()
            if type(targetfields) in (str, unicode):
                self.function = lambda id : factory(self.cachable.db, id, **{uplink: self.cachable})
            else:
                self.function = lambda *ids : factory(self.cachable.db, ids, **{uplink: self.cachable})
        else:
            self.function = _trivial
        self.reffield = reffield or cachable.__idcolumn__
        self.endfunc = endfunc or list
        self.orderby = orderby
        self.distinct = distinct
        self.filter = filter
    def retrieve(self):
        distinctstr = "distinct " if self.distinct else ""
        wherestr = ("WHERE %s" % sqlWhere(self.reffield, self.cachable.id)) if self.reffield else ""
        SQL = "SELECT %s%s FROM %s %s" % (distinctstr, _selectlist(self.targetfields), self.table, wherestr)
        if self.filter: SQL += " AND (%s)" % self.filter
        if self.orderby: SQL += " ORDER BY %s" % _selectlist(self.orderby)
        data = self.cachable.db.doQuery(SQL)
        return self.endfunc(self.function(*x) for x in data)

    def prepareCache(self,cacher):
        if self.cached: return
        if type(self.reffield) in (list, tuple): return
        fields = self.targetfields
        if type(fields) in (str, unicode): fields = [fields]
        cacher.addFKField(fields, self.table, self.reffield, self.orderby)

    def doCache(self, cacher):
        if self.cached: return
        if type(self.reffield) in (list, tuple): return
        fields = self.targetfields
        if type(fields) in (str, unicode): fields = [fields]
        data = cacher.getFKData(fields, self.table, self.cachable, self.reffield, self.orderby)
        val = self.endfunc(self.function(*x) for x in data)
        self.cache(val)

        
        
    
    # TODO: cache! not as easy as I thought# !
    # def prepareCache(self, cacher):
    #     # TODO: does not guarantee order!
    #     if type(self.targetfields) in (str, unicode):
    #         cacher.addDBField(self.targetfields, table=self.table)
    #     else:
    #         for field in self.targetfields:
    #             cacher.addDBField(field, table=self.table)

    # def doCache(self, cacher):
    #     if type(self.targetfields) in (str, unicode): 
    #         x = cacher.getDBData(self.cachable, self.targetfields, self.table)
    #     else:
    #         x = [cacher.getDBData(self.cachable, field, self.table) for field in self.targetfields]
    #     val = cacher.getDBData(self.cachable, self.fieldname, self.table)
    #     return self.endfunc(self.function(*x) for x in self.cachable.db.doQuery(SQL))

        
def _trivial(*args):
    if len(args) == 1: return args[0]
    return args

def _selectlist(fields):
    if type(fields) in (str, unicode): return "[%s]" % fields
    else: return ",".join("[%s]" % f for f in fields)
 
##################################
#      Property Factories        #
##################################
   
class PropertyFactory(object):
    def __init__(self, klass, *args, **kargs):
        self.klass = klass
        self.args = args
        self.kargs = kargs
    def createProperty(self, object, property):
        return self.klass(object, *self.args, **self.kargs)
        
class DBPropertyFactory(PropertyFactory):
    def __init__(self, *args, **kargs):
        PropertyFactory.__init__(self, DBProperty, *args, **kargs)
    def createProperty(self, object, property):
        if not self.args and not "fieldname" in self.kargs:
            self.args = (property,)
        return super(DBPropertyFactory, self).createProperty(object, property)        

class DBFKPropertyFactory(PropertyFactory):
    def __init__(self, *args, **kargs):
        PropertyFactory.__init__(self, DBFKProperty, *args, **kargs)
    def createProperty(self, object, property):
        if not self.args and not "fieldname" in self.kargs:
            self.args = (property,)
        return super(DBFKPropertyFactory, self).createProperty(object, property)

#DBFKProperty(self, cachable, table, targetfields, reffield=None, function=None, endfunc = None, orderby=None, dbfunc=None, factory=None, uplink=None, objfunc=None, distinct=False, filter=None):
   
class DBFKClassPropertyFactory(PropertyFactory):
    """Convenience class to create a property factory
    from a target class yielding table, targetfields, and dbfunc"""
    def __init__(self, targetklass, *args, **kargs):
        newargs = dict(table=targetklass.__table__, targetfields=targetklass.__idcolumn__, dbfunc=targetklass)
        newargs.update(kargs)
        PropertyFactory.__init__(self, DBFKProperty, *args, **newargs)
    def createProperty(self, object, property):
        return super(DBFKClassPropertyFactory, self).createProperty(object, property)

#####################################
# SQL String auxilliary functions   #
#####################################
    
def quotefield(s):
    if "(" in s: return s
    return "[%s]" % s
def quotefields(s):
    if type(s) in (str, unicode): s = [s]
    return ",".join(map(quotefield, s))

    
def sqlWhere(fields, ids):
    if type(fields) in (str, unicode):
        fields, ids = [fields], [ids]
    return "(%s)" % " and ".join("(%s = %s)" % (field, toolkit.quotesql(id))
                                 for (field, id) in zip(fields, ids))
        
def sqlFrom(cachables, table = None, reffield=None):
    c = cachables[0] # prototype, assume all cachables are alike
    if reffield is None: reffield = c.__idcolumn__
    if type(reffield) in (str, unicode):
        if type(c.id) <> int:
            raise TypeError("Singular reffield with non-int id! Reffield: %r, cachable: %r, id: %r" % (reffield, c, c.id))
        where  = toolkit.intselectionSQL(reffield, (x.id for x in cachables))
    else:
        where = "((%s))" % ") or (".join(sqlWhere(reffield, x.id) for x in cachables)

    return " FROM %s WHERE %s" % (table or c.__table__, where)

##################################
#    Optimization                #
##################################

class Cacher(object):
    """
    Object to gather data for multiple cachable objects and properties
    in as few SQL calls as possible
    """
    def __init__(self):
        self.dbfields = collections.defaultdict(set) # table : fields
        self.dbfkfields = set() # (table, reffield, fields)
    def getData(self, cachables):
        self.data = {} # {table, id} : {field : value}
        if type(cachables) not in (list, set):
            cachables = list(cachables)
        if not cachables: return
        prototype = cachables[0]
        db = prototype.db
        if not cachables: return
        for table, fields in self.dbfields.items():
            fields = list(fields)
            for batch in toolkit.splitlist(cachables, 5000):
                idcol = prototype.__idcolumn__
                if type(idcol) in (str, unicode): idcol = [idcol]
                SQL = "SELECT %s, %s %s" % (quotefields(prototype.__idcolumn__), quotefields(fields),
                                              sqlFrom(batch, table=table))
                for row in db.doQuery(SQL):
                    id, values = row[:len(idcol)], row[len(idcol):]
                    self.data[table, id] = dict(zip(fields, values))

        self.fkdata = collections.defaultdict(lambda  : collections.defaultdict(list)) # {table, reffield, fields, orderby} : {id : values}

        for table, reffield, fields, orderby in self.dbfkfields:
            for batch in toolkit.splitlist(cachables, 5000):
                SQL = "SELECT [%s], %s %s " % (reffield, ",".join(map(quotefield, fields)), sqlFrom(batch, table, reffield))
                if orderby: SQL += " ORDER BY %s" % orderby
                for row in cachables[0].db.doQuery(SQL):
                    id, values = row[0], row[1:]
                    self.fkdata[table, reffield,fields,orderby][id].append(values)
            
    def addDBField(self, field, table=None):
        self.dbfields[table].add(field)
        
    def getDBData(self, cachable, field, table=None):
        id = cachable.id
        if type(id) <> tuple: id = (id,)
        row = self.data.get((table, id))
        if row:
            if field not in row: print table, row
            return row[field]

    def addFKField(self, fields, table,  reffield, orderby):
        fields = tuple(fields)
        if type(reffield) == list: raise Exception(reffield)
        self.dbfkfields.add((table, reffield, fields, orderby))
    def getFKData(self, fields, table, cachable, reffield, orderby):
        fields = tuple(fields)
        return self.fkdata[table, reffield, fields, orderby].get(cachable.id, [])

def cacheMultiple(cachables, *propnames):
    """
    Cache the given propnames for the given cachables. If possible,
    uses a single SQL statement to cache for all objects.
    """
    if len(propnames)==1 and toolkit.isSequence(propnames[0], excludeStrings=True): propnames = propnames[0]
    if type(cachables) not in (list, tuple):
        if toolkit.isIterable(cachables, excludeStrings=True): cachables = list(cachables)
        else: cachables = [cachables]
    cacher = Cacher()
    for cachable in cachables:
        for propname in propnames:
            prop = cachable._getProperty(propname)
            if not prop: raise Exception("Cachable %r has not property %s" % (cachable, propname))
            prop.prepareCache(cacher)

    #toolkit.ticker.warn("Getting data")
    cacher.getData(cachables)
    #toolkit.ticker.warn("CAching values")
    for cachable in cachables:
        for prop in propnames:
            cachable._getProperty(prop).doCache(cacher)

def cache(cachables, *properties, **structure):
    """
    Cache properties and properties of (foreign key) properties
    Structure is a dict where the keys are properties of the cachable,
    If the property itself returns a (sequence of) cachable,
    the value in the structure can be a structure dict which is
    cached recursively on the retrieved cachable object(s).
    If the structure dictionary value is False (None, {}, ...), only
    the property itself is retrieved. *properties are treated as structure
    keys with a False value.
    example: cache([article1, article2], "headline", source=["name"])
             Caches the headline and source of these articles, and also
             caches the name of the source(s). 
    """
    # insert bare properties into structure, make surce cachables is iterable
    if len(properties)==1 and toolkit.isSequence(properties[0], excludeStrings=True): properties = properties[0]
    for prop in properties: structure[prop] = None
    if not toolkit.isIterable(cachables, excludeStrings=True): cachables = [cachables]
    # cache first layer
    cacheMultiple(cachables, structure.keys())
    # recurse into next layer
    for prop, struct in structure.iteritems():
        if struct:
            objects = set()
            for c in cachables:
                addendum = c.__getattribute__(prop)
                if not toolkit.isIterable(addendum, excludeStrings=False): addendum=[addendum]
                objects |= set(a for a in addendum if a)
            if type(struct) <> dict: struct = dict((k, False) for k in struct)
            cache(objects, **struct)
    
            
            
########################################
#          Driver                      #
########################################

if __name__ == '__main__':
    import dbtoolkit, article, project
    db  = dbtoolkit.amcatDB(profile=True)
    db.beforeQueryListeners.add(toolkit.warn)
    aids = 353570, 364425, 815672

    def illegalQuery(*args, **kargs): raise Exception("DB is disabled! Attempted to do:\ndoQuery(%s, %s)" % (map(str, args), kargs))
    _q = illegalQuery
    def toggleDB():
        global _q
        _q, db.doQuery = db.doQuery, _q
        
    print "--------- simple attribute getting ---------------"
    for aid in aids:
        toggleDB()
        a = article.Article(db, aid)
        print "Created article %i: %s" % (aid, id(a))
        toggleDB()
        print "  a.headline = %r" % a.headline
        print "  |a.sentences| = %i" % toolkit.count(a.sentences)

    print "--------- caching on init ---------------"
    for aid in aids:
        toggleDB()
        a = article.Article(db, aid, headline="TEST", sentences=[])
        print "Created article %i: %s" % (aid, id(a))
        print "  a.headline = %r" % a.headline
        print "  |a.sentences| = %i" % toolkit.count(a.sentences)
        toggleDB()
        
    print "--------- caching multiple properties, one article ---------------"
    for aid in aids:
        toggleDB()
        a = article.Article(db, aid)
        toggleDB()
        print "Created article %i: %s" % (aid, id(a))
        a.cacheProperties("encoding", "date", "headline")
        print "cached properties"
        toggleDB()
        print "  a.date = %r" % a.date
        print "  a.headline = %r" % a.headline
        toggleDB()

    print "--------- caching multiple properties, multiple cachables ---------------"
    toggleDB()
    arts = [article.Article(db, aid) for aid in aids]
    toggleDB()
    cache(arts, ["encoding", "date", "headline"])
    toggleDB()
    for a in arts:
        print "Article %i: %s" % (aid, id(a))
        print "  a.date = %r" % a.date
        print "  a.headline = %r" % a.headline
    toggleDB()

    print "--------- caching structure, multiple cachables ---------------"
    
    toggleDB()
    batch = project.Batch(db, 5563)
    toggleDB()
    cache(batch, "name", articles=dict(encoding={}, headline={}, source=["name"]))
    toggleDB()

    print "Batch.name: %s" % (batch.name)
    print "# Articles=%i" % len(batch.articles)
    for a in batch.articles:
        print "Article %i: %s" % (aid, id(a))
        print "  a.headline = %r" % a.headline
        print "  a.source = %s, .name=%s" % (a.source, a.source.name)
    toggleDB()
        
        
    print "\nQueries used:"
    db.printProfile()
