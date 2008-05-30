# import numarray, toolkit, gc
# eyal's attempt to bugfix 'ImportError: No module named numarray'
import numpy, toolkit, gc
from numpy import dot, transpose

ticker = toolkit.Ticker(100000)

def getsize(M):
    return map(int, M.readline().split(" "))

def readMatrix(f, maxCols = None, maxNRows = None, skipfirst = 1, colmap = None):
    m = []
    if skipfirst: f.readline()
    n = 0
    while 1:
        line = f.readline()
        if not line: break
        n += 1
        ticker.tick()
        if maxCols:
            m.append(map(float, line.split(" ")[:maxCols]))
        elif colmap:
            l = map(float, line.split(" "))
            r = map(lambda x:l[x], colmap)
            m.append(r)
        else:
            m.append(map(float, line.split(" ")))
        if maxNRows and n >= maxNRows: break

    if not m: return None
    return numarray.array(m)

def writeMatrix(M, printheader = 1):
    if printheader: print "%s %s" % M.shape
    for line in M:
        print " ".join(map(lambda x:`x`, line))

def readDiag(f, size):
    f.readline()
    result = numarray.zeros(size, numarray.Float32)
    ticker.reset()
    for line, i in toolkit.indexed(f):
        ticker.tick()
        result[i,i] = float(line)
    return result


import toolkit, struct, socket

class Writer:
    def __init__(self, outfile, binary):
        self.outfile = outfile
        self.binary = binary

    def write(self, *values, **kargs):
        for value in values:
            if self.binary:
                if toolkit.isFloat(value):
                    self.outfile.write(struct.pack("f", value))
                else:
                    self.outfile.write(struct.pack("l", socket.htonl(value)))
            else:
                format = toolkit.isFloat(value) and "%1.10f" or "%s"
                space = ("newline" in kargs) and "\n" or " "
                self.outfile.write((format+space) % (value))

    def writespaces(self, n, newline = False):
        if self.binary:
            self.write(*([0]*n))
        else:
            self.write(" "*(20*n), newline=newline)
            
    def rewind(self):
        self.outfile.seek(0,0)

class SparseMatrixWriter:
    def __init__(self, outfile,binary, skipHeader=True):
        self.writer = Writer(outfile, binary)
        self.skipped = skipHeader
        self.crc = [0,0,0]
        if skipHeader:
            self.reserveHeader()

    def reserveHeader(self):
        self.writer.writespaces(3, newline=True)
        
    def row(self, ncells):
        self.writer.write(ncells, newline=True)
        self.crc[1] += 1
        
    def cell(self, index, value):
        self.writer.write(index)
        self.writer.write(value, newline=True)
        self.crc[2] += 1
        if index > self.crc[0]: self.crc[0] = index-1
        
    def header(self, ncols=None, nrows=None, ncells=None):
        if not ncols: ncols=self.crc[0]
        if not nrows: nrows=self.crc[1]
        if not ncells: ncells=self.crc[2]
        
        try:
            if self.skipped:self.writer.rewind()
        except:
            toolkit.warn("Warning: could not seek() file, header is appended!")

        self.writer.write(ncols, nrows, ncells)


if __name__=='__main__':
    import sys
    colmap = [5,2,3]
    m = readMatrix(sys.stdin, 0,0,1,colmap)
    writeMatrix(m)
