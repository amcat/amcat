from itertools import izip
import struct, toolkit
import array
import tableoutput
import table3
import time, datetime
#import engine

class ColumnSerialiser(object):
    def serialiseValue(self, value, serialiser):
        pass
    def deserialiseValue(self, serialiser):
        pass
    def getSQLType(self):
        abstract
    def deserialiseSQL(self, value):
        return value
    def serialiseSQL(self, value):
        return value

class StringColumnSerialiser(ColumnSerialiser):
    def serialiseValue(self, value, socket):
        socket.sendstring(value)
    def deserialiseValue(self, socket):
        return socket.readstring()
    def getSQLType(self):
        return "varchar(5000)"
    def serialiseSQL(self, value):
        if value is None: return None
        if type(value) == str:
            return value.decode('latin-1')
        return value

def date2str(d):
    return d.isoformat()[:10]
def str2date(s):
    return datetime.datetime(*map(int, s.split("-")))
                              
class DateColumnSerialiser(ColumnSerialiser):
    def serialiseValue(self, value, socket):
        if type(value) == str: value = toolkit.readDate(value)
        if value is not None:
            value = date2str(value)
            #value = int(time.mktime(value.timetuple()))
        socket.sendstring(value)
    def deserialiseValue(self, socket):
        value = socket.readstring(checkerror=True)
        print "Received string %r" % value
        if value is not None:
            return str2date(value)#datetime.datetime(*time.gmtime(value)[:-2])
    def getSQLType(self):
        return "timestamp"
    def serialiseSQL(self, value):
        if value is None: return None
        return toolkit.writeDateTime(value)
    
class FloatColumnSerialiser(ColumnSerialiser):
    def serialiseValue(self, value, socket):
        socket.sendfloat(value)
    def deserialiseValue(self, socket):
        return socket.readfloat(checkerror=True)
    def getSQLType(self):
        return "real"
    
class IDLabelColumnSerialiser(ColumnSerialiser):
    def __init__(self, IDLabelFactory=None, concept=None):
        self.IDLabelFactory = IDLabelFactory
        self.concept = concept
    def serialiseValue(self, value, socket):
        if type(value) <> int:
            value = value.id
        socket.sendunsigned(value)
    def deserialiseValue(self, socket):
        value = socket.readunsigned(checkerror=True)
        if self.IDLabelFactory:
            #print "Deserialising %s" % value
            value = self.IDLabelFactory.get(self.concept, value)
            #print value
        return value
    def getSQLType(self):
        return "int"
    def serialiseSQL(self, value):
        if value is None: return None
        if type(value) == int: return value
        return value.id
    def deserialiseSQL(self, value):
        if self.IDLabelFactory:
            value = self.IDLabelFactory.get(self.concept, value)
        return value
        
            
class LabelProvider(object):
    def getLabel(self, val):
        return "%i" % val
class DBLabelProvider(object):
    def __init__(self, db, table, idcol="id", labelcol="label"):
        self.db = db
        self.table = table
        self.idcol = idcol
        self.labelcol = labelcol
        self.cache = None
    def getLabel(self, val):
        if self.cache is None:
            self.cache = dict(self.db.doQuery("select [%s], [%s] from [%s]" % (self.idcol, self.labelcol, self.table)))
        return self.cache.get(val, "?! %i" % val)
IDLABELCOLS ="article", "batch","storedresult", "subject","object","arrow","quality","project","source","actor","issue","brand","property", "coocissue", "customer", "set", "propertycluster"
STRINGCOLS = "headline","sourcetype", "url", "search"
FLOATCOLS = "sentiment", "quality","associationcooc","issuecooc"
DATECOLS = "date", "week","year"

def getColumns(concepts, IDLabelFactory=None):
    return (getColumn(c, IDLabelFactory) for c in concepts)

def getColumn(concept, IDLabelFactory=None):
    c = str(concept)
    if c in IDLABELCOLS:
        return IDLabelColumnSerialiser(IDLabelFactory=IDLabelFactory, concept=c)
    elif c in FLOATCOLS:
        return FloatColumnSerialiser()
    elif c in STRINGCOLS:
        return StringColumnSerialiser()
    elif c in DATECOLS:
        return DateColumnSerialiser()
    else:
        raise Exception("Unknown concept: %s" % c)


def serialise(columnserialisers, socket, data):
        if type(data) not in (list, tuple, set):
            data = list(data)
        print "Serialising %i rows x %i columns" % (len(data), len(columnserialisers))
        socket.sendint(len(data))
        for row in data:
            for c, s in izip(row, columnserialisers):
                s.serialiseValue(c, socket)

def serialiseConceptTable(table, socket):
    serialiseData(table.concepts, table.data, socket)

def serialiseData(concepts, data, socket):
    cols = list(getColumns(concepts))
    serialise(cols, socket, data)
    
def deserialise(columnserialisers, socket):
        nrows = socket.readint(checkerror=True)
        print "Deserialising %i rows x %i columns" % (nrows, len(columnserialisers))
        data = [None] * nrows
        for i in range(nrows):
            data[i] = [c.deserialiseValue(socket) for c in columnserialisers]
        return data

def deserialiseConceptTable(concepts, socket, idlabelfactory=None):
    return engine.ConceptTable(concepts,
                               deserialiseData(concepts, socket, idlabelfactory))

def deserialiseData(socket, concepts, idlabelfactory = None):
    cols = list(getColumns(concepts, idlabelfactory))    
    return deserialise(cols, socket)

    

def testserve(port=11111):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            s.bind(('', port))
            break
        except:
            port += 1
        
    s.listen(1)
    print "Listening to port %i" % port
    toolkit.writefile(str(port), "/tmp/port")
    conn, addr = s.accept()
    print "Connection from %s" % (addr,)
    c = ColumnTableDeserialiser(testcolumns(), conn)
    t = c.deserialiseTable()
    print tableoutput.table2ascii(t)
    
def testtable():
    import table3
    return table3.ListTable([[1,datetime.datetime.now(),3.45,"bafdsvgfdbvdfs"],[4,datetime.datetime.now(),6.1,"adsfasdf"],[7,datetime.datetime.now(),9.0,""]], ["a","b","c","?"])
    return table3.ListTable([[1,2,3.45],[4,5,6.1],[7,8,9.0]], ["a","b","c"])
def testcolumns():
    return [
        StructColumnSerialiser("i"),
        DateColumnSerialiser(),
        StructColumnSerialiser("f"),
        StringColumnSerialiser(),
        ]

def testclient():
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port = int(open('/tmp/port').read())
    print "CONNECTING TO %s" % port
    sock.connect(('127.0.0.1',port))
    c = ColumnTableSerialiser(testcolumns(), sock)
    t = testtable()
    print tableoutput.table2ascii(t)
    c.serialiseTable(t)
    sock.close()

def teststring():
    import io, socketio
    b = io.BytesIO()
    socket = socketio.AmcatSocket(b)
    c = ColumnTableSerialiser(testcolumns(), socket)
    t = testtable()
    c.serialiseTable(t)
    socket.flush()
    bytes = b.getvalue()
    

    b = io.BytesIO(bytes)
    socket = socketio.AmcatSocket(b)
    c2 = ColumnTableDeserialiser(testcolumns(), socket)
    t = c2.deserialiseTable()
    print tableoutput.table2unicode(t)
    
if __name__ == '__main__':
    import sys
    sys.argv += [""]
    if sys.argv[1] == "serve":
        testserve()
    elif sys.argv[1] == "client":
        testclient()
    else:
        teststring()
