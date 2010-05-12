from cachable import Cachable
import adapter, functools, ont2
from sys import maxint
from enum import Enum

RETURN = Enum(BOTH=-1, OBJECT=0, OMKLAP=1)

class Categorisation(Cachable):
    __table__ = 'o_categorisations'
    __idcolumn__ = 'categorisationid'
    __labelprop__ = "name"
    def __init__(self, ont, id):
        Cachable.__init__(self, ont.db, id)
        self.ont = ont
        self.addDBProperty("name")

        self.addDBFKProperty("classes", "o_categorisations_classes", "classid", function=ont.classes.get, orderby="order")
        self.addDBFKProperty("objects", "o_categorisations_objects", ("objectid", "order"),
                             function=lambda objid, order: (ont.nodes[objid], order), endfunc = dict)

    def categorise(self, obj, date=None, depth=[0,1,2], ret=RETURN.BOTH):
        def getSortKey(path):
            #print [self.objects.get(x[0], maxint) for x in path]
            return [self.objects.get(x[0], maxint) for x in path]


        result = None
        for clas in self.classes:
            paths = list(getPathsToRoot(obj, clas, date))

            if paths:
                paths.sort(key = getSortKey)
                result = paths[0]
                break
        if result is None: result = [(None, None)]

        if type(depth) == int:
            return thisOrLast(result, ret, depth)
        else:
            return map(functools.partial(thisOrLast, result, ret), depth)
                

def thisOrLast(seq, ret, i):
    if len(seq) <= i: result = seq[-1]
    else: result = seq[i]
    if ret == RETURN.BOTH: return result
    return result[ret.value]

def getPathsToRoot(path, clas, date=None):
    if type(path) <> list: path = [(path, 1)]
    head, headomklap = path[0]
                                 
    for (parent, omklap) in head.getParents(clas, date, True):
        #if omklap == -1: print parent
        p = [(parent, omklap * headomklap)] + path[:]
        if type(parent) == ont2.Class:
            yield p
        else:
            for p in getPathsToRoot(p, clas, date):
                yield p


                
if __name__ == '__main__':
    import dbtoolkit, ont2, time
    t = time.time()
    
    ont = ont2.fromDB(dbtoolkit.amcatDB())
    f = ont.categorisations[1]
    o = ont.objects[536]
    c = f.categorise(o)
    print c
    import sys;sys.exit(1)

    
    for clas in ont.classes.values():
        p = getPathsToRoot(ont.objects[2423], clas)
        for q in p:
            print clas.label, " - ".join("%s:%s (%s)" % (x[0].id, x[0].getLabel(), x[1]) for x in q)
        
    if c[0][0] is None:
        print "None!"
    else:
        print " - ".join("%s:%s (%s)" % (x[0].id, x[0].getLabel(), x[1]) for x in c)
        print " - ".join(x.getLabel() for x in f.categorise(ont.objects[2423], ret=RETURN.OBJECT))
        print " - ".join(str(x) for x in f.categorise(ont.objects[2423], ret=RETURN.OMKLAP))
