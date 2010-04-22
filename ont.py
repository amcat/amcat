from cachable import Cachable, DBFKPropertyFactory, DBPropertyFactory
import toolkit

def getParent(db, cid, pid):
    cl = Class(db, cid)
    if pid is None:
        return cl, None
    return cl, Object(db, pid)

    #return Class(db, cid), pid and Object(db, pid)

class Object(Cachable):
    __table__ = 'o_objects'
    __idcolumn__ = 'objectid'

    labels = DBFKPropertyFactory("o_labels", ("languageid", "label"), endfunc=dict)
    parents = DBFKPropertyFactory("o_hierarchy", ("classid", "parentid"), reffield="childid", dbfunc = getParent, endfunc=dict)
    children = DBFKPropertyFactory("o_hierarchy", ("classid", "childid"), reffield="parentid", dbfunc = getParent, endfunc=toolkit.multidict)

    name = DBPropertyFactory("name", table="o_politicians")
    firstname = DBPropertyFactory("firstname", table="o_politicians")
    prefix = DBPropertyFactory("prefix", table="o_politicians")

    label = DBPropertyFactory("label", table="o_labels")
    
    #@property
    #def label(self):
    #    l = self.labels
    #    if not l: return None
    #    return sorted(l.items())[0][1]

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
    def __getattr__(self, attr):
        if attr == "objekt": return super(self.__class__, self).__getattr__('objekt')
        return self.objekt.__getattribute__(attr)


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
    
    pickle.dumps(o)
    #print pickle.dumps(s)
    #print o.label
    #print list(o.children)
    

    
