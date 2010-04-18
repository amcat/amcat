from engineserver import readobj, sendobj, authenticateToServer, PORT
import socket
import engine
from engine import QueryEngine
import toolkit
import pooleddb
import dbtoolkit
import sqlite3
import cPickle as pickle
import table3

HOST = 'amcat.vu.nl'

class ProxyEngine(QueryEngine):
    def getList(self, *args, **kargs):
        print "Querying remote server..."
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST,PORT))
        authenticateToServer(s)
        sendobj(s, (args, kargs))
        x = readobj(s)
        if isinstance(x, Exception):
            raise x
        return x

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
    def __init__(self, engine, cachefile=None, caching=True):
        self.engine = engine
        self.db = dbtoolkit.amcatDB(SQLiteConfiguration(cachefile))
        if not cachefile: cachefile = toolkit.tempfilename(".sqlitedb")
        self.initcache()
        self.caching = caching
    def getList(self, concepts, filters, sortfields=None, limit=None, offset=None):
        result = self.getCachedList(concepts, filters)
        if not result:
            result = self.engine.getList(concepts, filters)
            if self.caching: self.cacheList(result, concepts, filters)
        engine.postprocess(result, sortfields, limit, offset)
        return result
    def serialize(self, obj):
        return pickle.dumps(obj)
    def deserialize(self, bytes):
        return pickle.loads(bytes)
    def getCachedList(self, concepts, filters):
        cflags = conceptflags(concepts)
        # use flags to check concepts are a subset of cached concepts
        # use >= check to allow index use, then check subset using A & B = A 
        for id, filters2 in self.db.doQuery("select id, filters from listcache where concepts >= %i and concepts & %i == %i" % (cflags, cflags, cflags)): 
            filters2 = self.deserialize(filters2)
            if filters <> filters2: continue
            result = self.db.getValue("select result from listcache where id=%i" % id)
            result = self.deserialize(result)
            result = postcache(result, concepts)
            return result
    def cacheList(self, result, concepts, filters):
        result, filters = map(self.serialize, (result, filters))
        concepts = conceptflags(concepts)
        self.db.insert("listcache", dict(concepts=concepts, filters=filters, result=result), retrieveIdent=False)
        self.db.commit()
    def initcache(self):
        if not self.db.doQuery("SELECT name FROM sqlite_master WHERE name='listcache'"):
            print "Creating cache tables"
            for cmd in CACHE_INIT_SQL:
                self.db.doQuery(cmd)
            self.db.commit()

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
id integer primary key autoincrement,
concepts integer,
filters blob,
result blob)""",
    "create index ix_listcache_concepts on listcache (concepts)"]

