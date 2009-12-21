import toolkit

class Cacher(object):
    def __init__(self):
        self.dbfields = []
    def getData(self, cachables):
        SQL = "SELECT [%s], %s %s" % (cachables[0].__idcolumn__,
                                      ",".join("[%s]" % f for f in self.dbfields), sqlFrom(cachables))
        print "-->", SQL
        self.data = {} # --> database query
    def addDBField(self, field):
        if field not in self.dbfields: self.dbfields.append(field)
        
    def getDBData(self, cachable, field):
        return "[%s::%s]" % (cachable.id, field)
        return self.data[self.dbfields.index(field)+1]

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
    def __init__(self, cachable, fieldname, func=None, table=None):
        Property.__init__(self, cachable)
        self.fieldname = fieldname
        self.func = func
        self.processedValue = None
        self.processedCached = False
        self.table = table
    def get(self):
        if not self.processedCached:
            val = Property.get(self)
            if self.func: val = self.func(val)
            self.processedValue = val
            self.processedCached = True
        return self.processedValue
    def retrieve(self):
        SQL = "SELECT %s %s" % (self.fieldname, self.cachable.sqlFrom(self.table))
        val = self.cachable.db.getValue(SQL)
        return val
    def prepareCache(self, cacher):
        cacher.addDBField(self.fieldname)
    def doCache(self, cacher):
        val = cacher.getDBData(self.cachable, self.fieldname)
        self.cache(val)
    
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
    def __init__(self, cachable, table, targetfields, reffield=None, function=None, endfunc = None, orderby=None):
        FunctionProperty.__init__(self, cachable, self.retrieve)
        self.table = table
        self.targetfields = targetfields
        self.function = function or trivial
        self.reffield = reffield or cachable.__idcolumn__
        self.endfunc = endfunc or trivial
        self.orderby = orderby
    def retrieve(self):
        #print self.reffield, self.cachable.id
        SQL = "SELECT %s FROM %s WHERE %s" % (selectlist(self.targetfields), self.table, sqlWhere(self.reffield, self.cachable.id))
        if self.orderby: SQL += " ORDER BY %s" % selectlist(self.orderby)
        return self.endfunc([self.function(*x) for x in self.cachable.db.doQuery(SQL)])

def sqlWhere(fields, ids):
    if type(fields) in (str, unicode):
        fields, ids = [fields], [ids]
    return "(%s)" % " and ".join("(%s = %s)" % (field, toolkit.quotesql(id))
                                 for (field, id) in zip(fields, ids))
        
def sqlFrom(cachables, table = None):
    c = cachables[0] # prototype, assume all cachables are alike
    if type(c.__idcolumn__) in (str, unicode):
        where = "(%s in (%s))" % (c.__idcolumn__, ",".join(str(x.id) for x in cachables))
    else:
        where = "((%s))" % ") or (".join(sqlWhere(x.__idcolumn__, x.id) for x in cachables)

    return " FROM %s WHERE %s" % (table or c.__table__, where)

def cacheMultiple(cachables, propnames):
    cacher = Cacher()
    for cachable in cachables:
        for prop in propnames:
            cachable.__properties__[prop].prepareCache(cacher)
    cacher.getData(cachables)
    for cachable in cachables:
        for prop in propnames:
            cachable.__properties__[prop].doCache(cacher)

class Cachable(toolkit.IDLabel):
    def __init__(self, db, id):
        self.db = db
        self.id = id
        self.__properties__ = {}
    def __getattr__(self, attr):
        if attr in self.__properties__:
            return self.__properties__[attr].get()
        # implement IDLabel.label in case no 'label' property exists.
        # Try __labelprop__ first, then try 'name'
        if attr == "label":
            try:
                attr = self.__labelprop__
            except AttributeError:
                attr = "name"
            return self.__getattr__(attr)
        raise AttributeError(attr)
    def addDBProperty(self, property, fieldname=None, func=None, table=None):
        if fieldname == None: fieldname = property
        self.addProperty(property, DBProperty(self, fieldname, func, table))
    def addFunctionProperty(self, property, func):
        self.addProperty(property, FunctionProperty(self, func))
    def addDBFKProperty(self, property, *args, **kargs):
        self.addProperty(property, DBFKProperty(self, *args, **kargs))
    def addProperty(self, propname, prop):
        self.__properties__[propname] = prop
    def cacheValues(self, **values):
        for prop, val in values.iteritems():
            self.__properties__[prop].cache(val)
    def removeCached(self, prop):
        self.__properties__[prop].uncache()
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

    for aid in aids:
        a = article.Article(db, aid)
        print "Created article %i: %s" % (aid, id(a))
        print "  a.headline = %r" % a.headline
        print "  |a.sentences| = %i" % toolkit.count(a.sentences)

    for aid in aids:
        a = article.Article(db, aid)
        print "Created article %i: %s" % (aid, id(a))
        a.cacheProperties("headline", "date")
        print "cached properties"
        print "  a.headline = %r" % a.headline
        print "  a.date = %r" % a.date

    print "\nQueries used:"
    p.printreport()
