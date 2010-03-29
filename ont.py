from cachable import Cachable, DBFKPropertyFactory
import toolkit

def getParent(db, cid, pid):
    return Class(db, cid), pid and Object(db, pid)

class Object(Cachable):
    __table__ = 'o_objects'
    __idcolumn__ = 'objectid'

    labels = DBFKPropertyFactory("o_labels", ("languageid", "label"), endfunc=dict)
    parents = DBFKPropertyFactory("o_hierarchy", ("classid", "parentid"), reffield="childid", dbfunc = getParent, endfunc=dict)
    children = DBFKPropertyFactory("o_hierarchy", ("classid", "childid"), reffield="parentid", dbfunc = getParent, endfunc=toolkit.multidict)
    
    @property
    def label(self):
        l = self.labels
        if not l: return None
        return sorted(l.items())[0][1]

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
    db = dbtoolkit.amcatDB(profile=True)
    import dbpoolclient
    db = dbpoolclient.ProxyDB()
    
    s = Class(db, 5001)
    o = BoundObject(10002, 16222, db)
    print pickle.dumps(o)
    print pickle.dumps(s)
    

    
