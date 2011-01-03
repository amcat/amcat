import socket, io, time
import struct
import math
import sys

UNSIGNED_STRUCT = None
UNSIGNED_ERROR = '\xff\xff\xff\xff' # struct.pack("I", 2**32-1) == struct.pack("i", -1) (!)
UNSIGNED_ERROR_VALUE = 2**32 - 1
UNSIGNED_NULL = '\xfe\xff\xff\xff' # struct.pack("I", 2**32-2)
UNSIGNED_NULL_VALUE = 2**32 - 2
UNSIGNED_MAXINT = 2**32 - 3

INT_STRUCT = None
FLOAT_STRUCT = None


class AmcatSocket(io.BufferedRWPair):
    def __init__(self, socket):
        io.BufferedRWPair.__init__(self, socket, socket)
        self._socket = socket
        
        
    def sendstruct(self, data, struct):
        try:
            bytes = struct.pack(*data)
        except Exception, e:
            raise Exception("Exception on packing %s into %s: %s" % (data, struct, e))
        self.write(bytes)
    def readstruct(self, struct):
        bytes = self.read(struct.size)
        #print "Read bytes %r for struct %s" % (bytes, struct.format)
        if len(bytes) < struct.size:
            raise Exception("Server unexpectedly closed network connection")
        return struct.unpack(bytes)

    def sendunsigned(self, i):
        if i is None:
            self.write(UNSIGNED_NULL)
        else:
            if i < 0 or i > UNSIGNED_MAXINT: raise Exception("Unsigned cannot represent %i" % i)
            global UNSIGNED_STRUCT
            if UNSIGNED_STRUCT is None: UNSIGNED_STRUCT = struct.Struct("I")
            self.sendstruct((i,), UNSIGNED_STRUCT)
    def readunsigned(self, checkerror=True):
        global UNSIGNED_STRUCT
        if UNSIGNED_STRUCT is None: UNSIGNED_STRUCT = struct.Struct("I")
        val = self.readstruct(UNSIGNED_STRUCT)[0]
        if val == UNSIGNED_NULL_VALUE: return None
        if checkerror and (val == UNSIGNED_ERROR_VALUE): 
            str = self.readstring()
            raise Exception("Exception from server: %s" % str)
        return val
        
    def readint(self, checkerror=False):
        global INT_STRUCT
        if INT_STRUCT is None: INT_STRUCT = struct.Struct("?i")
        #print "Reading int"
        val = readtuple(self.readstruct(INT_STRUCT))
        #print "Val", val
        if checkerror and val == -1:
            str = self.readstring()
            raise Exception("Exception from server: %s" % str)
        return val

    
    def sendint(self, i):
        global INT_STRUCT
        if INT_STRUCT is None: INT_STRUCT = struct.Struct("?i")
        self.sendstruct(gettuple(i), INT_STRUCT)
    def readint(self, checkerror=False):
        global INT_STRUCT
        if INT_STRUCT is None: INT_STRUCT = struct.Struct("?i")
        #print "Reading int"
        val = readtuple(self.readstruct(INT_STRUCT))
        #print "Val", val
        if checkerror and val == -1:
            str = self.readstring()
            raise Exception("Exception from server: %s" % str)
        return val

    def sendfloat(self, f):
        global FLOAT_STRUCT
        if FLOAT_STRUCT is None: FLOAT_STRUCT = struct.Struct("?f")
        self.sendstruct(gettuple(f), FLOAT_STRUCT)
    def readfloat(self, checkerror=False):
        global FLOAT_STRUCT
        if FLOAT_STRUCT is None: FLOAT_STRUCT = struct.Struct("?f")
        val = readtuple(self.readstruct(FLOAT_STRUCT))
        if val and checkerror and math.isnan(val):
            str = self.readstring()
            raise Exception("Exception from server: %s" % str)
        return val

    def sendstring(self, s):
        if s is None:
            self.sendunsigned(None)
        else:
            bytes = str(s)
            #print "Sending %i characters" % len(bytes)
            self.sendunsigned(len(bytes))
            self.write(bytes)
    def readstring(self, checkerror=True):
        strlen = self.readunsigned(checkerror=checkerror)
        #print "Reading %i characters" % strlen
        if strlen is None: return None
        elif strlen == 0: return ""
        else:
            bytes = self.read(strlen)
            return bytes

    def senderror(self, e):
        self.sendint(-1)
        self.sendstring(str(e))


def gettuple(val):
    if val is None: return (True, -99)
    else: return (False, val)
def readtuple(tuple):
    none, val = tuple
    if none: return None
    return val
        
def connect(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print "CONNECTING TO %s:%s" % (host, port)
    s.connect((host,port))
    return AmcatSocket(SocketIO(s))

class SocketIO(io.RawIOBase):
    """wrapper around a socket object to implement io interface.
    Batteries included, huh?""" 
    def __init__(self, socket):
        self.socket = socket
        if type(socket) == AmcatSocket: raise Exception()
    def readable(self): return self.socket is not None
    def writable(self): return self.socket is not None
    def write(self, bytes):
        #print "Sending %i bytes" % (len(bytes),)
        return self.socket.send(bytes)
    def read(self, n=4096):
        data = self.socket.recv(n)
        #print "Read %i bytes: %r (n=%i)" % (len(data), data, n)
        return data
    def readall(self):
        raise Exception("READALL")
    def readinto(self, b):
        raise Exception("READINTO")
    def close(self):
        self.socket.close()

SOCKET = None
        
def serve(port, host='', callback=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    global SOCKET; SOCKET = sock
    while True:
        try:
            sock.bind((host, port))
            break
        except Exception, e:
            if "Address already in use" in str(e):
                print "Waiting for port %i to become available" % port
                time.sleep(2)
            else:
                raise
    try:
        sock.listen(1)
        print "Listening to port %s:%s" % (host, port)
        if callback: callback()
        while True:
            conn, addr = sock.accept()
            yield AmcatSocket(SocketIO(conn))
    finally:
        try:
            sock.close()
        except:
            pass
    

if __name__ == '__main__':
    if False:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost',1235))
        f = SocketIO(s)
    else:
        import io
        f = io.BytesIO()
    rw = io.BufferedRWPair(f, f)
    
    print "writing"
    rw.write('123')
    time.sleep(.05)
    print "writing"
    rw.write('456')
    time.sleep(.05)
    print "Flushing"
    rw.flush()
    
    d = rw.read(6)
    print "read", d
    
