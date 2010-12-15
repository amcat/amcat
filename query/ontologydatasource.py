import datasource
import article
#import ont2
import ont
import lucenelib
import toolkit
import collections
import categorise
import cachable
import amcatmetadatasource # mappedfield


class OntologyDataSource(datasource.DataSource):
    def __init__(self, dm, db, index, mappings=None, idlabellang=None):
        self.db = db
        datasource.DataSource.__init__(self, mappings)
        self._ont = None
        self.index = index
        self.idlabellang=idlabellang

#    @property
#    def ont(self):
#        if self._ont == None:
#            self._ont = ont2.fromDB(self.db)
#        return self._ont
    
    def getOntologyField(self, concept):
        for mapping in self.getMappings():
            for field in (mapping.a,mapping.b):
                if isinstance(field, OntologyField) and field.concept == concept:
                    return field

    def getPossibleValues(self, concept):
        f = self.getOntologyField(concept)
        if f: return f.getObjects()

    def deserialize(self, concept, id):
        f = self.getOntologyField(concept)
        if f:
            if type(id) == int: 
                id = f.getObject(id)
            return id


class OntArtField(datasource.Field):
    def __init__(self, ds, concept, ontfield):
        datasource.Field.__init__(self, ds, concept)
        self.ontfield = ontfield
        
            
class OntArt(object):
    def __init__(self, obj, article, cooc):
        self.obj = obj
        self.article = article
        self.cooc = cooc
        
class OntArtObjectMapping(datasource.Mapping):
    def __init__(self,a,b):
        datasource.Mapping.__init__(self, a, b, 100.0, 99999999)
    def map(self, value, reverse, memo=None):
        if reverse:
            raise Exception("Not supported")
        return [value.obj]
class OntArtCoocMapping(datasource.Mapping):
    def __init__(self,a,b):
        datasource.Mapping.__init__(self, a, b, 100.0, 99999999)
    def map(self, value, reverse, memo=None):
        if reverse:
            raise Exception("Not supported")
        return [value.cooc]

class HierarchyMapping(datasource.Mapping):
    def map(self, value, reverse, memo):
        if reverse: # map child -> parent
            return [value.parent]
        else: # map parent -> child
            return value.children

class SetObjectsMapping(datasource.Mapping):
    def __init(self, a, b):
        datasource.Mapping.__init__(self, a, b, 1.0, 99999999)
    def map(self, value, reverse, memo):
        if reverse: raise Exception("object -> set mapping not implemented")
        if type(value) == int: value = self.a.getObject(value)
        return value.objects
        
    
class ArticleOntArtMapping(datasource.Mapping):
    def map(self, value, reverse, memo=None):
        if reverse:
            yield value.article
            return
        if memo is None: memo = self.startMapping([value])
        if type(memo) != dict:
            memo = dict(memo)
        of = self.b.ontfield
        objects = list(of.getObjects())
        for object in objects:
            values = list(memo.get(object.id, []))
            if not values:
                toolkit.warn("No values for object %r" % object)
            cooc = int(value in values)
            yield OntArt(object, value, cooc)

    def startMapping(self, values, reverse=False):
        if reverse: return
        of = self.b.ontfield
        objects = of.getObjects()
        target = list((o, of.getAllObjects(o)) for o in objects)
        return list(self.a.datasource.index.searchMultiple(target))

class OntologyField(amcatmetadatasource.MappedField):
    def getObjects(self):
        "return sequence of ont2.Objects visible in this field"
        abstract
    def getQuery(self, object):
        "given an ont2.Object, return the xapian query to search it"
        abstract
#    @property
#    def ont(self):
 #       return self.datasource.ont

class SetField(OntologyField):
    def getObject(self, id):
        return ont.Set(self.datasource.db, id)

class SetOntologyField(OntologyField):
    def __init__(self, ds, concept, setid, supersetid, catid=None, conceptmapper=None):
        OntologyField.__init__(self, ds, concept, conceptmapper=conceptmapper)
        self.setid = setid
        self.supersetid = supersetid
        self._set = None
        self._superset = None
        self.objectsPerObject = None
    @property
    def superset(self):
        if self._superset is None:
            self._superset = ont.Set(self.datasource.db, self.supersetid)
        return self._superset
    @property
    def set(self):
        if self._set is None:
            self._set = ont.Set(self.datasource.db, self.setid)
        return self._set
    def getObjects(self):
        return self.set.objects
    def getAllObjects(self, object):
        if self.objectsPerObject is None:
            toolkit.ticker.warn("Setting up")
            children = collections.defaultdict(list)

            objects = set(self.superset.objects)
            target = set(self.set.objects)
            toolkit.ticker.warn("Caching")
            #cachable.cacheMultiple(objects, "functions", "keyword", "labels", "name", "firstname", "parents")
            cachable.cacheMultiple(objects | target, "functions", "keyword", "labels", "name", "firstname", "parents")
            toolkit.ticker.warn("Computing children")
            for o in objects:
                if o in target: continue
                parents = list(o.getAllParents())
                for p in parents:
                    if p in objects or p in target:
                        children[p].append(o)
                        break
            def allchildren(o):
                yield o
                for o2 in children.get(o, []):
                    for c in allchildren(o2):
                        yield c
            self.objectsPerObject = dict((o.id,list(allchildren(o))) for o in target)
        if type(object) <> int: object = object.id
        return self.objectsPerObject[object]
    def getQuery(self, object):
        objects = set(self.getAllObjects(object))
        objects.add(object)
        query = " OR ".join("(%s)" % o.getSearchString() for o in objects)
        if type(query) == str: query = query.decode('latin-1')
        query = query.encode('ascii','replace')
        return query
    def getObject(self, id):
        return ont.Object(self.datasource.db, id)

class HierarchyOntologyField(OntologyField):
    def __init__(self, ds, concept, objectid, classid, depth=1, queryIncludesSelf=True):
        OntologyField.__init__(self, ds, concept)
        self.classid = classid
        if ds.db and classid:
            self.klass = ont.Class(ds.db, classid)
            if objectid:
                self.object = self.klass.getBoundObject(objectid)
        else:
            self.klass, self.object = None, None
        self.depth = depth
        self.queryIncludesSelf = queryIncludesSelf
    def getObjects(self):
        return getDescendants(self.object, self.depth)
    def getAllObjects(self, object):
        return getDescendants(object)
    def getQuery(self, object):
        return " OR ".join("(%s)" % o for o in getDescendants(object))
    def getObject(self, id):
        return self.klass.getBoundObject(id)
    #return ont.BoundObject(self.classid, id, self.datasource.db)
        
def getDescendants(root, depth=None):
    for child in root.getChildren():
        yield child
        if (depth is None) or (depth > 1): 
            for child2 in getDescendants(child, depth and depth-1):
                yield child2

class ObjectArticleMapping(datasource.Mapping):
    def __init__(self, a, b, db):
        datasource.Mapping.__init__(self, a, b, 1, 100000000)
        self.db = db

    def map(self, value, reverse, memo=None):
        if reverse:
            raise Exception("Article -> Ontology Object mapping not implemented")
        #toolkit.warn("ObjectArticleMapping value=%s" % value)
        
        objects = self.a.getAllObjects(value)
        objects = list(objects)
        #toolkit.warn("> %s -> %s" % (value, map(str, objects)))
        return self.a.datasource.index.search(objects)

if __name__ == '__main__':
    import dbtoolkit, toolkit
    class X(object): pass
    ds = X()
    ds.db = dbtoolkit.amcatDB(profile=True)
    #ds.db.beforeQueryListeners.add(toolkit.ticker.warn)
    f = SetOntologyField(ds, None, 5002, 5000)

    import lucenelib
    INDEX = "/home/jpakraal/dnnluc"
    import objectfinder
    lf = objectfinder.LuceneFinder(ds.db, 13)
    for o in f.getObjects():
        if o.id <> 14243: continue
        s =  lf.getQueries(f.getAllObjects(o))
        print s
        
        try:
            lucenelib.search(INDEX, dict(s=s).items())
        except Exception, e:
            print f.getAllObjects(o)
            print s
            print o.id
            print e
    ds.db.printProfile()
    
