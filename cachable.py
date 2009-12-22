import toolkit, collections
from functools import partial
import weakref

def quotefield(s):
    if "(" in s: return s
    return "[%s]" % s

class Cacher(object):
    def __init__(self):
        self.dbfields = collections.defaultdict(set) # table : fields
    def getData(self, cachables):
        if not cachables: return
        self.data = {}
        for table, fields in self.dbfields.items():
            fields = list(fields)
            SQL = "SELECT [%s], %s %s" % (cachables[0].__idcolumn__, ",".join(map(quotefield, fields)),
                                            sqlFrom(cachables, table=table))
            for row in cachables[0].db.doQuery(SQL):
                self.data[table, row[0]] = dict(zip(fields, row[1:]))
    def addDBField(self, field, table=None):
        self.dbfields[table].add(field)
        
    def getDBData(self, cachable, field, table=None):
        row = self.data.get((table, cachable.id))
        if row:
            if field not in row: print table, row
            return row[field]

class Property(object):
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
    def __init__(self, cachable, fieldname, func=None, table=None, objfunc=None, dbfunc=None):
        Property.__init__(self, cachable)
        self.fieldname = fieldname
        self.func = func
        self.objfunc = objfunc
        self.dbfunc = dbfunc
        self.table = table
    def process(self, *values):
        if self.func: return self.func(*values)
        if self.objfunc: return self.objfunc(self.cachable, *values)
        if self.dbfunc: return self.dbfunc(self.cachable.db, *values)
        return values[0]
    def retrieve(self):
        seq = type(self.fieldname) in (list, tuple)
        if seq:
            field = ",".join(map(quotefield, self.fieldname))
        else:
            field = quotefield(self.fieldname)

        SQL = "SELECT %s %s" % (field, self.cachable.sqlFrom(self.table))
        d = self.cachable.db.doQuery(SQL)
        if d: return self.process(*d[0])
    def prepareCache(self, cacher):
        cacher.addDBField(self.fieldname, table=self.table)
    def doCache(self, cacher):
        val = cacher.getDBData(self.cachable, self.fieldname, self.table)
        self.cache(self.process(val))

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
class FunctionProperty(Property):
     def __init__(self, cachable, func):
        Property.__init__(self, cachable)
        self.retrieve =  func

def trivial(*args):
    if len(args) == 1: return args[0]
    return args

def selectlist(fields):
    if type(fields) in (str, unicode): return "[%s]" % fields
    else: return ",".join("[%s]" % f for f in fields)

class DBFKProperty(FunctionProperty):
    def __init__(self, cachable, table, targetfields, reffield=None, function=None, endfunc = None, orderby=None, dbfunc=None, factory=None, uplink=None):
        FunctionProperty.__init__(self, cachable, self.retrieve)
        self.table = table
        self.targetfields = targetfields
        if function:
            self.function = function
        elif dbfunc:
            self.function = partial(dbfunc, self.cachable.db)
        elif factory:
            if uplink is None: uplink = type(cachable).__name__.lower()
            factory = factory()
            if type(targetfields) in (str, unicode):
                self.function = lambda id : factory(self.cachable.db, id, **{uplink: self.cachable})
            else:
                self.function = lambda *ids : factory(self.cachable.db, ids, **{uplink: self.cachable})
        else:
            self.function = trivial
        self.reffield = reffield or cachable.__idcolumn__
        self.endfunc = endfunc or trivial
        self.orderby = orderby
    def retrieve(self):
        #print self.reffield, self.cachable.id
        SQL = "SELECT %s FROM %s WHERE %s" % (selectlist(self.targetfields), self.table, sqlWhere(self.reffield, self.cachable.id))
        if self.orderby: SQL += " ORDER BY %s" % selectlist(self.orderby)
        return self.endfunc([self.function(*x) for x in self.cachable.db.doQuery(SQL)])

class DBFKPropertyFactory(PropertyFactory):
    def __init__(self, *args, **kargs):
        PropertyFactory.__init__(self, DBFKProperty, *args, **kargs)
    def createProperty(self, object, property):
        if not self.args and not "fieldname" in self.kargs:
            self.args = (property,)
        return super(DBFKPropertyFactory, self).createProperty(object, property)

def sqlWhere(fields, ids):
    if type(fields) in (str, unicode):
        fields, ids = [fields], [ids]
    return "(%s)" % " and ".join("(%s = %s)" % (field, toolkit.quotesql(id))
                                 for (field, id) in zip(fields, ids))
        
def sqlFrom(cachables, table = None):
    c = cachables[0] # prototype, assume all cachables are alike
    if type(c.__idcolumn__) in (str, unicode):
        where  = toolkit.intselectionSQL(c.__idcolumn__, (x.id for x in cachables))
    else:
        where = "((%s))" % ") or (".join(sqlWhere(x.__idcolumn__, x.id) for x in cachables)

    return " FROM %s WHERE %s" % (table or c.__table__, where)

def cacheMultiple(cachables, propnames):
    if not toolkit.isSequence(propnames, excludeStrings=True):
        propnames = [propnames]
    cacher = Cacher()
    for cachable in cachables:
        for prop in propnames:
            cachable._getProperty(prop).prepareCache(cacher)
    cacher.getData(cachables)
    for cachable in cachables:
        for prop in propnames:
            cachable._getProperty(prop).doCache(cacher)
            
_CACHE = {}
class CachingMeta(type):
    def __call__(cls, id, *args, **kargs):
        cancache = cls.__dict__.get('__cacheme__')
        if cancache and (cls, id) in _CACHE:
            obj = _CACHE[cls, id]()
            if obj is not None: return obj
        obj = type.__call__(cls, id, *args, **kargs)
        if cancache: _CACHE[cls, id] = weakref.ref(obj)
        return obj

class Cachable(toolkit.IDLabel):
    __metaclass__ = CachingMeta
    def __init__(self, db, id, **cache):
        self.db = db
        self.id = id
        self.__properties__ = {}
        for k,v in cache.iteritems():
            if k is not None:
                self.cacheValues(**{k:v})
        
    def _getProperty(self, attr):
        prop = self.__properties__.get(attr)
        if prop is not None: return prop
        factory = type(self).__dict__.get(attr)
        if isinstance(factory, PropertyFactory):
            prop = factory.createProperty(self, attr)
        if not prop:
            dbprops = type(self).__dict__.get("__dbproperties__", ())
            if attr in dbprops:
                prop = DBProperty(self, attr)
        if prop:
            self.__properties__[attr] = prop
            return prop
    def __getattribute__(self, attr):
        if attr <> "__properties__" and attr <> '_getProperty':
            prop = self._getProperty(attr)
            if prop:
                return prop.get()
        try:
            return toolkit.IDLabel.__getattribute__(self, attr)
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
        self.addProperty(property, DBProperty(self, fieldname or property, func, table))
    def addFunctionProperty(self, property, func):
        self.addProperty(property, FunctionProperty(self, func))
    def addDBFKProperty(self, property, *args, **kargs):
        self.addProperty(property, DBFKProperty(self, *args, **kargs))
    def addProperty(self, propname, prop):
        self.__properties__[propname] = prop
    def cacheValues(self, **values):
        for prop, val in values.iteritems():
            p = self._getProperty(prop)
            if not p: raise AttributeError("Cannot find property %s of %r" % (prop, self))
            p.cache(val)
    def removeCached(self, prop):
        self._getProperties(prop).uncache()
    def cacheProperties(self, *propnames):
        cacheMultiple([self], propnames)
    def sqlFrom(self, table=None):
        return sqlFrom([self], table)


    
if __name__ == '__main__':
    import dbtoolkit, article
    db  = dbtoolkit.amcatDB()
    db.beforeQueryListeners.append(toolkit.ticker.warn)
    p = dbtoolkit.ProfilingAfterQueryListener()
    db.afterQueryListeners.append(p)
    aids = 353570, 364425, 815672

    print "--------- simple attribute getting ---------------"
    for aid in aids:
        a = article.Article(db, aid)
        print "Created article %i: %s" % (aid, id(a))
        print "  a.headline = %r" % a.headline
        print "  |a.sentences| = %i" % toolkit.count(a.sentences)
        
    print "--------- caching multiple properties, one article ---------------"
    for aid in aids:
        a = article.Article(db, aid)
        print "Created article %i: %s" % (aid, id(a))
        a.cacheProperties("date", "headline", "encoding")
        print "cached properties"
        print "  a.date = %r" % a.date
        print "  a.headline = %r" % a.headline

    print "--------- caching multiple properties, multiple cachables ---------------"
    arts = [article.Article(db, aid) for aid in aids]
    cacheMultiple(arts, ["date", "headline", "encoding"])
    for a in arts:
        print "Article %i: %s" % (aid, id(a))
        print "  a.date = %r" % a.date
        print "  a.headline = %r" % a.headline
        
    print "\nQueries used:"
    p.printreport()
