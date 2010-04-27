from cachable import Cachable, DBFKPropertyFactory, DBPropertyFactory
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

def getAllAncestors(object, stoplist=None):
    if stoplist is None: stoplist = set()
    for p in object.parents.values():
        if (p is None) or (p in stoplist): continue
        yield p
        stoplist.add(p)
        for o2 in getAllAncestors(p, stoplist):
            yield o2


class Object(Cachable):
    __table__ = 'o_objects'
    __idcolumn__ = 'objectid'

    labels = DBFKPropertyFactory("o_labels", ("languageid", "label"), endfunc=dict)
    parents = DBFKPropertyFactory("o_hierarchy", ("classid", "parentid"), reffield="childid", dbfunc = getParent, endfunc=dict)
    children = DBFKPropertyFactory("o_hierarchy", ("classid", "childid"), reffield="parentid", dbfunc = getParent, endfunc=toolkit.multidict)

    name = DBPropertyFactory("name", table="o_politicians")
    firstname = DBPropertyFactory("firstname", table="o_politicians")
    prefix = DBPropertyFactory("prefix", table="o_politicians")
    keyword = DBPropertyFactory(table="o_keywords")

    label = DBPropertyFactory("label", table="o_labels")

    def getSearchString(self, date=None, xapian=False):
        if not date: date = my_datetime.now()
        if self.keyword: return self.keyword.replace("\n"," ")
        if self.name:
            ln = self.name
            if "-" in ln or " " in ln:
                ln = '"%s"' % ln.replace("-", " ")
            conds = []
            if self.firstname:
                conds.append(self.firstname)
            for p, fro, to in self.getParties(date):
                k = p.getSearchString()
                if not k: k = '"%s"' % str(p).replace("-"," ")
                conds.append(k)
            for f, p, fro, to in self.getFunctions(date):
                k = p.getSearchString()
                if not k: k = '"%s"' % str(p).replace("-"," ")
                conds.append(k)
                conds += function2conds(f, p)
            if conds:
                if xapian:
                    kw = "%s AND (%s)" % (ln, " OR ".join("%s" % x.strip() for x in conds),)
                else:
                    kw = "%s AND (%s)" % (ln, " OR ".join("%s^0" % x.strip() for x in conds),)
            else:
                kw = ln
            return kw.replace("\n"," ")

    # anders??
    def getParties(self, date=None):
        SQL = "select party_objectid, fromdate, todate from o_politicians_parties where objectid=%i" % self.id
        if date: SQL += " and fromdate < %s and (todate is null or todate > %s)" % (toolkit.quotesql(date), toolkit.quotesql(date))
        for p, fro, to in self.db.doQuery(SQL):
            yield Object(self.db, p), fro, to
    def getFunctions(self, date=None):
        SQL = "select functionid, office_objectid, fromdate, todate from o_politicians_functions where objectid=%i" % self.id
        if date: SQL += "and fromdate < %s and (todate is null or todate > %s)""" % (toolkit.quotesql(date), toolkit.quotesql(date))
        for f, p, fro, to in self.db.doQuery(SQL):
            yield f, Object(self.db, p), fro, to
            
    #@property
    #def label(self):
    #    l = self.labels
    #    if not l: return None
    #    return sorted(l.items())[0][1]

# anders!
def function2conds(func, office):
    if office.id in (380, 707, 729, 1146, 1536, 1924, 2054, 2405, 2411, 2554, 2643):
        if func == 2:
            return ["bewinds*", "minister*"]
        else:
            return ["bewinds*", "staatssecret*"]
    if office.id == 901:
        return ["premier", '"minister president"']
    if office.id == 548:
        return ["senator", '"eerste kamer*"']
    if office.id == 1608:
        return ["parlement*", '"tweede kamer*"']
    if office.id == 2087:
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
    @property
    def label(self):
        return self.objekt.label
    def __str__(self):
        return str(self.objekt)
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

class Set(Cachable):
    __table__ = 'o_sets'
    __idcolumn__ = 'setid'
    __dbproperties__ = ["name"]
    objects = DBFKPropertyFactory("o_sets_objects", "objectid", dbfunc=Object)
    

if __name__ == '__main__':
    import dbtoolkit, pickle

    pickle.dumps(getParent)
    
    db = dbtoolkit.amcatDB(profile=True)
    
    s = Class(db, 5001)
    o = BoundObject(10002, 16222, db)
    print o.children

    o = BoundObject(10002, 16595, db)
    list(o.children)
    for k, v in o.__properties__.items():
        print `k`, `v`

        for k2, v2 in v.__dict__.items():
            print `k2`, `v2`
            pickle.dumps(v2)
            print "OK"
        
        pickle.dumps(v)
        
        print "OK"
                          
    pickle.dumps(o.__properties__)

    #print pickle.dumps(o)
    #print pickle.dumps(s)
    

    pickle.dumps(o)
    #print pickle.dumps(s)
    #print o.label
    #print list(o.children)
    
