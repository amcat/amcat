import datasource
import article
import ont2
import ont
import lucenelib
import toolkit
import collections

TEST_INDEX = "/home/amcat/indices/Test politiek nieuws 2010-02-15T12:35:36"

class OntologyDataSource(datasource.DataSource):
    def __init__(self, dm, db, index, mappings=None):
        # kargs = dict(username='draft', password='l0weL)WE')
        self.db = db
        datasource.DataSource.__init__(self, mappings)
        self._ont = None
        self.index = index

    @property
    def ont(self):
        if self._ont == None:
            self._ont = ont2.fromDB(self.db)
        return self._ont
    
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
            if type(id) <> int: return id
            return f.getObject(id)


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
        datasource.Mapping.__init__(self, a, b, 1.0, 99999999)
    def map(self, value, reverse, memo=None):
        if reverse:
            raise Exception("Not supported")
        return [value.obj]
class OntArtCoocMapping(datasource.Mapping):
    def __init__(self,a,b):
        datasource.Mapping.__init__(self, a, b, 1.0, 99999999)
    def map(self, value, reverse, memo=None):
        if reverse:
            raise Exception("Not supported")
        return [value.cooc]

class ArticleOntArtMapping(datasource.Mapping):
    def map(self, value, reverse, memo=None):
        if reverse:
            yield value.article
            return
        if memo is None: memo = self.startMapping([value])
        of = self.b.ontfield
        objects = of.getObjects()
        for object in objects:
            cooc = int(value.id in memo.get(object.id, {}))
            yield OntArt(object, value, cooc)

    def lucenehack(self, query):
        return lucenelib.search(TEST_INDEX, query.items())[0]
    
    def getArticles(self, query, subset=None):
        print "Query", query
        if self.a.datasource.index is None:
            return self.lucenehack(query)
        else:
            i = self.a.datasource.index
            return dict((k, set(i.query(v, returnAID=True, subset=subset))) for (k,v) in query.iteritems())

    def startMapping(self, values, reverse=False):
        if reverse: return
        of = self.b.ontfield
        objects = of.getObjects()
        query = dict((o.id, of.getQuery(o)) for o in objects)
        return self.getArticles(query, subset=values)

class OntologyField(datasource.Field):
    def getObjects(self):
        "return sequence of ont2.Objects visible in this field"
        abstract
    def getQuery(self, object):
        "given an ont2.Object, return the xapian query to search it"
        abstract
    @property
    def ont(self):
        return self.datasource.ont
    
class SetOntologyField(OntologyField):
    def __init__(self, ds, concept, setid, supersetid, catid):
        OntologyField.__init__(self, ds, concept)
        self.setid = setid
        self.supersetid = supersetid
        self.catid = catid
    def getObjects(self):
        return self.ont.sets[self.setid].objects
    def getAllObjects(self, object):
        c = self.ont.categorisations[self.catid]
        for o2 in self.ont.sets[self.supersetid].objects:
            parents = c.categorise(o2, depth=[0,1,2,3,4,5,6,7,8,9], ret=categorise.RETURN.OBJECT)
            if object in parents:
                yield o2
    def getQuery(self, object):
        objects = set(self.getAllObjects(object))
        objects.add(object)
        query = " OR ".join("(%s)" % o.getSearchString() for o in objects)
        if type(query) == str: query = query.decode('latin-1')
        query = query.encode('ascii','replace')
        return query
    def getObject(self, id):
        return self.ont.objects[id]

class HierarchyOntologyField(OntologyField):
    def __init__(self, ds, concept, objectid, classid, depth=1, queryIncludesSelf=True):
        OntologyField.__init__(self, ds, concept)
        self.object = ont.BoundObject(classid, objectid, ds.db)
        self.depth = depth
        self.queryIncludesSelf = queryIncludesSelf
    def getObjects(self):
        return getDescendants(self.object, self.depth)    
    def getQuery(self, object):
        return " OR ".join("(%s)" % o for o in getDescendants(object))
    def getObject(self, id):
        return ont.BoundObject(self.object.klasse.id, id, self.datasource.db)
        
def getDescendants(root, depth=None):
    for child in root.children:
        yield child
        if (depth is None) or (depth > 1): 
            for child2 in getDescendants(child, depth and depth-1):
                yield child2

class ObjectArticleMapping(datasource.Mapping):
    def __init__(self, a, b, db):
        datasource.Mapping.__init__(self, a, b, -10)
        self.db = db

    def lucenehack(self, query):
        results = lucenelib.search(TEST_INDEX, {"X" : q}.items())
        for aid in results[0]["X"].keys():
            yield article.Article(self.db, aid)

    def getArticles(self, query):
        #raise Exception(query)
        print "Query", query
        print "Index", self.a.datasource.index and self.a.datasource.index.location
        if self.a.datasource.index is None:
            return self.lucenehack(query)
        else:
            return self.a.datasource.index.query(query, acceptPhrase=True)

    def map(self, value, reverse, memo=None):
        if reverse:
            raise Exception("Article -> Ontology Object mapping not implemented")
        q = self.a.getQuery(value)
        return self.getArticles(q)

