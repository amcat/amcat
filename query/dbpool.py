"""
DBPool - receives DB requests on a socket and distributes among
worker threads, each having a DB connection.

Threads:
1) Listener - listens to requests, reads request and places on queue
2) Workers - wait on queue, execute request
"""

import threading, Queue, socket, struct, cPickle, time, traceback, sys
#import toolkit, tableoutput, dbtoolkit

SOCKETPORT = 14330

def connect(username, password):
    host = "Easysoft-AmcatDB"
    import mx.ODBC.unixODBC as driver
    return driver.connect(host, username, password)

def execute(db, sql, select=None):
    if type(sql) == unicode: sql = sql.encode('latin-1', 'replace')
    if select is None:
        select=sql.lower().strip().startswith("select")
    c = None
    try:
        c = db.cursor()
        c.execute(sql)
        if select:
            return c.fetchall() 
    finally:
        if c:
            try:
                c.close()
            except:
                pass
    
class ListenerThread(threading.Thread):
    def __init__(self, requestqueue, port=SOCKETPORT):
        threading.Thread.__init__(self)
        self.queue = requestqueue
        self.port = port
    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                s.bind(('127.0.0.1',self.port))
                break
            except Exception, e:
                if "Address already in use" in str(e):
                    print "Waiting for port %i to become available" % self.port
                    time.sleep(2)
                else:
                    raise
        s.listen(1)
        print >>sys.stderr, ("Listening to port %i" % self.port)
        while True:
            conn, addr = s.accept()
            #print >>sys.stderr, ("Accepted connection from %s" % (addr,))
            self.queue.put(conn)

class WorkerThread(threading.Thread):
    def __init__(self, requestqueue, name=None):
        threading.Thread.__init__(self, name=(name or "Worker-%i" % id(self)))
        self.queue = requestqueue
        self.stop = False
        self.db = connect(username='draft', password='l0weL)WE')
    def run(self):
        while not self.stop:
            try:
                conn = self.queue.get(True, .1)
            except Queue.Empty:
                if self.stop: return
                continue
            sql = None
            try:
                data = r''
                sql= readi(conn)
                print >>sys.stderr, ("Handling request SQL %r" % sql)
                try:
                    data = execute(self.db, sql)
                except Exception, e:
                    self.db.rollback()
                    print >>sys.stderr, ("Exception on executing SQL: %s" % e)
                    traceback.print_exc()
                    print e, e.sql
                    data = cPickle.dumps(e, True)
                else:
                    self.db.commit()
                    if data: # Memory leak stops if this is 'if False:'
                        print >>sys.stderr, ("Successfully queried %i rows" % (len(data), ))
                        data = cPickle.dumps(data, True)
                    else:
                        print >>sys.stderr, ("No results")
                        data = cPickle.dumps(None, True)
                #print >>sys.stderr, ("Sending results (%i bytes)" % len(data))
                sendi(conn, data)
            except Exception, e:
                print >>sys.stderr, ("Exception on handling request %s: %s" % (sql, e))
                traceback.print_exc()
            finally:
                del data
                conn.close()

def serve(port=SOCKETPORT, nworkers=16):
    queue = Queue.Queue(500)
    workers = [WorkerThread(queue, "dbpool.Worker-%i" % i)
               for i in range(nworkers)]
    for worker in workers: worker.start()
    server = ListenerThread(queue, port)
    server.start()
    server.join()
    for worker in workers:
        worker.stop = True
   
############ Aux Methods ################
   
STRUCTFMT = 'I'
STRUCTLEN = struct.calcsize(STRUCTFMT)
READBUF = 4096

def readi(conn):
    i = conn.recv(STRUCTLEN)
    if not i: raise Exception("Connection closed")
    i, = struct.unpack(STRUCTFMT, i)
    #toolkit.warn("receiving %i bytes" % i)
    data = ""
    while len(data) < i:
        remainder = min(READBUF, i - len(data))
        data += conn.recv(remainder)
        #toolkit.warn("received %i bytes" % len(data))
    #print "Received %i bytes: %i:%r" % (i, len(data), data)
    return data

def sendi(conn, str):
    conn.send(struct.pack(STRUCTFMT, len(str)))
    conn.send(str)

def usage():
    print "Usage: dbpool [-pPORT] start serving on PORT (default 14330)"
    sys.exit()
    
############## Driver ###################
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        usage()
    port = SOCKETPORT
    if  len(sys.argv) > 1 and sys.argv[1].startswith("-p"):
        port = int(sys.argv[1][2:])
    print port
    serve(port)
