import threading
import Queue
import functools
import toolkit
import traceback
import sys
import time
import hashlib
import uuid
import tableserial
import filter
import socketio

from servertools import *

NWORKERS = 5

DISPATCH = {} # request_id : function(socket)

# EngineServer protocol version 1
#   - All integers "i" sent as struct.pack('i', i) bytes
#   - All bytestrings "s" sent as "i" strlen plus i bytes
#   - At any time, if an error occurs, server sends integer -1 (ff.ff.ff.ff) followed by the error string
#     As a consequence, every server response should start with something that can be checked as an error
#     ie a string, non-zero integer, or float
# 1. Client connects, sends expected version number "i"
# 2. Server sends maxium supported version followed by a random challenge string
# 3. Client sends 16 byte md5 hash of challenge bytes using shared key
# 4. Client sends request "i"
#    a) if request == REQUEST_LIST:
#     a1) Client sends NUM_CONCEPTS "i" and NUM_FILTERS "i"
#     a2) for each concept client sends concept id "i"
#     a3) for each filter client sends concept id "i"
#        followed by serialised data (using tableserial protocol)
#     a4) server sends concept list data (using tableserial protocol)
#   b)if request == REQUEST_QUOTE
#     b1) Client sends articleid "i"
#     b2) Client sends space separated quote words as one string
#     b3) Server sends quote string

DISPATCH[1] = lambda sock : sock

def authenticateClient(socket):
    challenge = uuid.uuid4().bytes
    hashed = hash(challenge)
    socket.sendstring(challenge)
    socket.flush()

    response = socket.read(16)
    if hashed <> response:
        #print "Sent challenge %r, hashed with key %r, received response %r<>%r" % (challenge, KEY, response, hashed)
        raise Exception("Access denied")

def serverhandshake(socket):
    version = socket.readint()
    if version <> 1: raise Exception("Unknown protocol version: %i" % version)
    print "client version %iu connected, snending server version" % version
    socket.sendint(1) # server version
    authenticateClient(socket)
    socket.sendint(1) # authenticated OK, ready for request
    socket.flush()

class WorkerThread(threading.Thread):
    def __init__(self, queue, engine):
        threading.Thread.__init__(self, name="Worker-%i" % id(self))
        self.queue = queue
        self.stop = False
        self.engine = engine
    def run(self):
        while not self.stop:
            try:
                socket = self.queue.get(True, .1)
            except Queue.Empty:
                if self.stop: return
                continue
            try:
                serverhandshake(socket)
                print "Shook hands"
                request = socket.readint()
                DISPATCH[request](socket, self.engine)
            except Exception, e:
                traceback.print_exc(file=sys.stdout)
                socket.senderror(e)
            finally:
                print "Closing connection"
                socket.close()

def getFilter(type, concept, data):
    if type == FILTER_INTERVAL:
        (todate,), (fromdate,) = data
        return filter.IntervalFilter(concept, todate, fromdate)
    else:
        return filter.ValuesFilter(concept, *[x for (x,) in data])
    
def getList(socket, engine, distinct=False):
    nconcepts = socket.readint()
    nfilters = socket.readint()
    conceptnames = [socket.readstring() for i in range(nconcepts)]
    concepts = map(engine.model.getConcept, conceptnames)
    filters = []
    for f in range(nfilters):
        type = socket.readint()
        conceptname = socket.readstring()

        concept = engine.model.getConcept(conceptname)
        data = tableserial.deserialiseData(socket, [concept])
        filters.append(getFilter(type, concept, data))
        print "Fitler type %i, Concept %s, data %r" % (type, concept, data)
    data = engine.getList(concepts, filters ,distinct=distinct)
    tableserial.serialiseData(concepts, data, socket)
    socket.close()
        
    
DISPATCH[REQUEST_LIST] = getList

def getDistinctList(socket, engine):
    getList(socket, engine, distinct=True)

DISPATCH[REQUEST_LIST_DISTINCT] = getDistinctList

def getQuote(socket, engine):
    articleid = socket.readint()
    quotewords = socket.readstring()
    quote = engine.getQuote(articleid, quotewords)
    socket.sendstring(quote)
    socket.close()
    

DISPATCH[REQUEST_QUOTE] = getQuote

def createServer(engine, port=PORT, nworkers=NWORKERS, callback=None):    
    requestq = Queue.Queue()
    for i in range(NWORKERS):
        WorkerThread(requestq, engine).start()
    for sock in socketio.serve(port, callback=callback):
        requestq.put(sock)

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1])
    import dbtoolkit; db = dbtoolkit.amcatDB()
    import amcatmetadatasource; dm = amcatmetadatasource.getDataModel(db)
    import engine; e = engine.QueryEngine(dm, db)
    createServer(e, port=port)
    
