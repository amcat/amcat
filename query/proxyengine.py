from engineserver import readobj, sendobj, authenticateToServer, PORT
import socket
import engine
from engine import QueryEngine
import toolkit
import pooleddb
import dbtoolkit
import sqlite3
import cPickle as pickle
#import pickle
import filter
import engineserver
import table3

HOST = 'amcat.vu.nl'

def serialize(x):
    print type(x)
    return x

class ProxyEngine(QueryEngine):
    def __init__(self, datamodel, log=False, profile=False, port=PORT):
        self.port = port
        QueryEngine.__init__(self, datamodel, log, profile)
    
    def getList(self, *args, **kargs):
        print "Querying remote server..."
        return self.remoteCall("getList", args, kargs)

    def remoteCall(self, call, args, kargs):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print "CONNECTING TO %s" % self.port
        s.connect((HOST,self.port))
        authenticateToServer(s)
        sendobj(s, (call, args, kargs))
        x = readobj(s)
        if isinstance(x, Exception):
            raise x
        return x
    
    def getQuote(self, *args, **kargs):
        return self.remoteCall("getQuote", args, kargs)

class SQLiteConfiguration(object):
    def __init__(self, filename=None):
        self.filename = filename or toolkit.tempfilename(".sqlitedb")
        self.drivername = "sqlite"
        self.database = "cache"
    def connect(self, *args, **kargs):
        con = sqlite3.connect(self.filename)
        con.text_factory = str
        return con

class CachingEngineWrapper(QueryEngine):
    def __init__(self, engine, cachedb, caching=True):
        self.engine = engine
        self.cachedb = cachedb
        self.initcache()
        self.caching = caching
    def getList(self, concepts, filters, sortfields=None, limit=None, offset=None, distinct=False):
        result = None
        try:
            result = self.getCachedList(concepts, filters, distinct)
        except Exception, e:
            import traceback
            traceback.print_exc()
        if not result:
            result = self.engine.getList(concepts, filters, distinct=distinct)
            if self.caching: self.cacheList(result, concepts, filters, distinct)
        engine.postprocess(result, sortfields, limit, offset)
        return result

    def serializeValue(self, val):
        if type(val) == int: return val
        return val.id
    
    def serializefilters(self, filters):
        return self.serialize(filters)
        filterlist = []
        for f in filters:
            cid= f.concept.id
            if type(f) == filter.ValuesFilter:
                filterlist += [("Values", cid) + tuple(map(self.serializeValue, f.values))]
            else:
                raise Exception("Unknown filter type: %s" % type(f))
        return self.serialize(filterlist)
    def deserializefilters(self, bytes):
        return self.deserialize(bytes)
        filterlist = self.deserialize(bytes)
        result = []
        for t in filterlist:
            filtertype, cid = t[:2]
            concept = self.engine.model.getConcept(cid)
            if filtertype == "Values":
                 result += [filter.ValuesFilter(concept, *t[2:])]
            else:
                raise Exception("!")
        return result
    def serialize(self, obj):
        b = pickle.dumps(obj)
        return buffer(b)
    def deserialize(self, bytes):
        b = str(bytes)
        return pickle.loads(b)
    def getCachedList(self, concepts, filters, distinct):
        cflags = conceptflags(concepts)
        # use flags to check concepts are a subset of cached concepts
        # use >= check to allow index use, then check subset using A & B = A
        toolkit.ticker.warn("Querying cache")
        cached = self.cachedb.doQuery("select id, filters, distnct from listcache where concepts >= %i and concepts & %i = %i" % (cflags, cflags, cflags))
        toolkit.ticker.warn("Iterating over %i promising candidates" % (len(cached)))
        for id, filters2, distinct2 in cached:
            if distinct2 <> distinct: continue
            filters2 = self.deserializefilters(filters2)
            print `filters`, `filters2`, filters == filters2
            if filters <> filters2: continue
            toolkit.ticker.warn("Found direct match: %i" % (id))
            result = self.cachedb.getValue("select result from listcache where id=%i" % id)
            toolkit.ticker.warn("Deserializing")
            result = self.deserialize(result)
            toolkit.ticker.warn("Postcache")
            result = postcache(result, concepts)
            toolkit.ticker.warn("Done")
            return result
    def cacheList(self, result, concepts, filters, distinct):
        engineserver.cachelabels(result)

        toolkit.ticker.warn("Serializing")
        result, filters = self.serialize(result), self.serializefilters(filters)
        concepts = conceptflags(concepts)
        toolkit.ticker.warn("Inserting")
        cacheid = self.cachedb.insert("listcache", dict(concepts=concepts, filters=filters, result=result, distnct=distinct))
        self.cachedb.commit()
        toolkit.ticker.warn("Done")
        
    def initcache(self):
        if not self.cachedb.hasTable("listcache"):
            print "Creating cache tables"
            for cmd in CACHE_INIT_SQL:
                self.cachedb.doQuery(cmd)
            self.cachedb.commit()

            
    def getQuote(self, article, words):
        words = " ".join(toolkit.getQuoteWords(words))
        try:
            q = self.getCachedQuote(article, words)
            if q:
                toolkit.warn("Retrieved quote from cache")
            else:
                toolkit.warn("Querying underlying engine for quote")
                q = self.engine.getQuote(article, [words])
                self.cacheQuote(article, words, q)
            return q
        except:
            return self.engine.getQuote(article, [words])

    def getCachedQuote(self, article, words):
        return self.cachedb.getValue("select quote from quotecache where aid = %i and words='%s'" % (article.id, words)) 
    def cacheQuote(self, article, words, quote):
        self.cachedb.insert("quotecache", dict(aid=article.id, words=words, quote=quote), retrieveIdent=False)
        self.cachedb.commit()
            

class ConceptSubTable(table3.Table):
    def __init__(self, conceptTable, concepts):
        self.concepts = concepts
        self.data = conceptTable.data
        self.dataconcepts = conceptTable.concepts
    def getRows(self): return self.data
    def getColumns(self): return self.concepts
    def getValue(self, row, col):
        return row[self.dataconcepts.index(col)]

def postcache(table, concepts):
    if table.concepts == concepts:  return table
    return ConceptSubTable(table, concepts)
    
    

def conceptflags(concepts):
    result = 0
    for concept in concepts:
        result += pow(2, concept.id)
    return result

CACHE_INIT_SQL = [
    """create table listcache (
id serial primary key,
concepts integer,
filters bytea,
distnct boolean,
result bytea)""",
    "create index ix_listcache_concepts on listcache (concepts)",
"""create table quotecache (
aid integer,
words varchar(4000),
quote varchar(4000),
primary key (aid, words))"""
]

