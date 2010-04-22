from engineserver import readobj, sendobj, authenticateToServer, PORT
import socket
import engine
from engine import QueryEngine
import toolkit
import pooleddb
import dbtoolkit
import sqlite3
#import cPickle as pickle
import pickle

import table3

HOST = 'amcat.vu.nl'

class ProxyEngine(QueryEngine):
    def getList(self, *args, **kargs):
        print "Querying remote server..."
        return self.remoteCall("getList", args, kargs)

    def remoteCall(self, call, args, kargs):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST,PORT))
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
        result = self.getCachedList(concepts, filters, distinct)
        if not result:
            result = self.engine.getList(concepts, filters, distinct=distinct)
            if self.caching: self.cacheList(result, concepts, filters, distinct)
        engine.postprocess(result, sortfields, limit, offset)
        return result
    def serializefilters(self, filters):
        return self.serialize(filters)
    def deserializefilters(self, bytes):
        return self.deserialize(bytes)
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
        for id, filters2, distinct2 in self.cachedb.doQuery("select id, filters, distnct from listcache where concepts >= %i and concepts & %i = %i" % (cflags, cflags, cflags)):
            if distinct2 <> distinct: continue
            filters2 = self.deserializefilters(filters2)
            print filters, filters2, filters==filters2
            if filters <> filters2: continue
            print "Getting cached result"
            result = self.cachedb.getValue("select result from listcache where id=%i" % id)
            result = self.deserialize(result)
            result = postcache(result, concepts)
            return result
    def cacheList(self, result, concepts, filters, distinct):
        result, filters = self.serialize(result), self.serializefilters(filters)
        #result, filters = map(self.serialize, (result, filters))
        concepts = conceptflags(concepts)
        cacheid = self.cachedb.insert("listcache", dict(concepts=concepts, filters=filters, result=result, distnct=distinct))
        self.cachedb.commit()
        
    def initcache(self):
        if not self.cachedb.hasTable("listcache"):
            print "Creating cache tables"
            for cmd in CACHE_INIT_SQL:
                self.cachedb.doQuery(cmd)
            self.cachedb.commit()
    def getQuote(self, *args, **kargs):
        return self.engine.getQuote(*args, **kargs)

            

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
    "create index ix_listcache_concepts on listcache (concepts)"]

