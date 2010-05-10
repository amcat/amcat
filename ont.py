from cachable import Cachable, DBFKPropertyFactory, DBPropertyFactory, CachingMeta, cache
import toolkit
try:
    import mx.DateTime as my_datetime
except:
    from datetime import datetime as my_datetime
    
def getParent(db, cid, pid):
    cl = Class(db, cid)
    if pid is None:
        return cl, None
    return cl, Object(db, pid)

    #return Class(db, cid), pid and Object(db, pid)

def getAllAncestors(object, stoplist=None, golist=None):
    if stoplist is None: stoplist = set()
    for p in object.getAllParents():
        if (p is None) or (p in stoplist): continue
        if (golist and p not in golist): continue
        yield p
        stoplist.add(p)
        for o2 in getAllAncestors(p, stoplist, golist):
            yield o2

def getAllDescendants(object, stoplist=None, golist=None):
    if stoplist is None: stoplist = set()
    for p in object.children:
        if (p is None) or (p in stoplist): continue
        if (golist and p not in golist): continue
        yield p
        stoplist.add(p)
        for o2 in getAllDescendants(p, stoplist, golist):
            yield o2

def getObject(db, id):
    return Object(db, id)

DATEFILTER = "fromdate < %s and (todate is null or todate > %s)" % (toolkit.quotesql(my_datetime.now()), toolkit.quotesql(my_datetime.now()))

class Function(object):
    def __init__(self, db, functionid, office_objectid, fromdate, todate):
        self.functionid = functionid
        self.office = Object(db, office_objectid)
        if fromdate.year == 1753: fromdate = None
        self.fromdate = fromdate
        self.todate = todate
    def __str__(self):
        return "Function(%s, %s, %s, %s)" % (self.functionid, self.office, self.fromdate and toolkit.writeDate(self.fromdate), self.todate and toolkit.writeDate(self.todate))
    __repr__ = __str__

class Object(Cachable):
    __table__ = 'o_objects'
    __idcolumn__ = 'objectid'
    __metaclass__ = CachingMeta


    labels = DBFKPropertyFactory("o_labels", ("languageid", "label"), endfunc=dict)
    parents = DBFKPropertyFactory("o_hierarchy", ("classid", "parentid"), reffield="childid", dbfunc = getParent, endfunc=dict)
    children = DBFKPropertyFactory("o_hierarchy", ("classid", "childid"), reffield="parentid", dbfunc = getParent, endfunc=toolkit.multidict)

    name = DBPropertyFactory("name", table="o_politicians")
    firstname = DBPropertyFactory("firstname", table="o_politicians")
    prefix = DBPropertyFactory("prefix", table="o_politicians")
    keyword = DBPropertyFactory(table="o_keywords")


    functions = DBFKPropertyFactory("o_politicians_functions", ("functionid", "office_objectid", "fromdate", "todate"), dbfunc = Function)

    def __init__(self, db, id, languageid=2, **cache):
        Cachable.__init__(self, db, id, **cache)
        self.addDBProperty("label", table="dbo.fn_o_labels(%i)" % languageid)

    def getAllParents(self, date=None):
        for p in self.parents.values():
            if p:
                yield p
        for f in self.currentFunctions(date):
            yield f.office
        
    def currentFunctions(self, date=None):
        for f in self.functions:
            if f.fromdate and date < f.fromdate: continue
            if f.todate and date >= f.todate: continue
            yield f
    
    def getSearchString(self, date=None, xapian=False, languageid=None, fallback=False):
        """Returns the search string for this object.
        date: if given, use only functions active on this date
        xapian: if true, do not use ^0 weights
        languageid: if given, use labels.get(languageid) rather than o_keywords"""
        
        if not date: date = my_datetime.now()
        if languageid:
            kw = self.labels.get(languageid)

        if (not languageid) or (fallback and kw is None):
            kw = self.keyword
        
        if not kw and self.name:
            ln = self.name
            if "-" in ln or " " in ln:
                ln = '"%s"' % ln.replace("-", " ")
            conds = []
            if self.firstname:
                conds.append(self.firstname)
            for function in self.currentFunctions(date):
                k = function.office.getSearchString()
                if not k: k = '"%s"' % str(function.office).replace("-"," ")
                conds.append(k)
                conds += function2conds(function)
            if conds:
                if xapian:
                    kw = "%s AND (%s)" % (ln, " OR ".join("%s" % x.strip() for x in conds),)
                else:
                    kw = "%s AND (%s)" % (ln, " OR ".join("%s^0" % x.strip() for x in conds),)
            else:
                kw = ln
        if kw:
            if type(kw) == str: kw = kw.decode('latin-1')
            return kw.replace("\n"," ")


def function2conds(function):
    officeid = function.office.id
    if officeid in (380, 707, 729, 1146, 1536, 1924, 2054, 2405, 2411, 2554, 2643):
        if function.functionid == 2:
            return ["bewinds*", "minister*"]
        else:
            return ["bewinds*", "staatssecret*"]

    if officeid == 901:
        return ["premier", '"minister president"']
    if officeid == 548:
        return ["senator", '"eerste kamer*"']
    if officeid == 1608:
        return ["parlement*", '"tweede kamer*"']
    if officeid == 2087:
        return ['"europ* parlement*"', "europarle*"]
    return []

class BoundObject(toolkit.IDLabel):
    def __init__(self, klasse, objekt, db=None):
        if type(klasse) == int:
            if not db: raise Exception("If klasse is the classid, db is required")
            klasse = Class(db, klasse)
        self.klasse = klasse
        if type(objekt) == int:
            objekt = Object(klasse.db, objekt)
        self.objekt = objekt
        toolkit.IDLabel.__init__(self, self.objekt.id, None)
    @property
    def parent(self):
        # try/catch to avoid triggering __getattr__ on deeper AttributeError
        try:
            parent = self.objekt.parents[self.klasse]
            if parent:
                return BoundObject(self.klasse, parent)
        except AttributeError, e:
            raise Exception(e)
    @property
    def children(self):
        # try/catch to avoid triggering __getattr__ on deeper AttributeError
        try:
            children = self.objekt.children[self.klasse]
            if children:
                for child in children:
                    yield BoundObject(self.klasse, child)
        except AttributeError, e:
            raise Exception(e)

    def label(self, languageid=None):
        return self.objekt.label
    def __str__(self):
        return str(self.objekt)
    def getSearchString(self, *args, **kargs):
        return self.objekt.getSearchString( *args, **kargs)
#    def __getattr__(self, attr):
#        return self.objekt.__getattribute__(attr)
#    def __getattr__(self, attr):
#        if attr == "objekt": return super(self.__class__, self).__getattr__('objekt')
#        return self.objekt.__getattribute__(attr)


class Class(Cachable):
    __table__ = 'o_classes'
    __idcolumn__ = 'classid'
    __dbproperties__ = ["label"]
    objects = DBFKPropertyFactory("o_hierarchy", "childid", objfunc=BoundObject)

    def getRoots(self, cachefirst=True):
        objs = self.objects
        if cachefirst: cache([o.objekt for o in objs], "parents")
        for o in objs:
            if not o.parent:
                yield o
        
class Set(Cachable):
    __table__ = 'o_sets'
    __idcolumn__ = 'setid'
    __dbproperties__ = ["name"]
    __metaclass__ = CachingMeta
    objects = DBFKPropertyFactory("o_sets_objects", "objectid", dbfunc=Object)
    

if __name__ == '__main__':
    import dbtoolkit, pickle, cachable

    db = dbtoolkit.amcatDB(profile=True)

    for i in [1,2,5,13]:
        print i, Object(db, 412, i)
    db.printProfile()
