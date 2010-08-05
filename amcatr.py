import rpy2.robjects as robjects
import rpy2.rlike.container as rlc 
import table3, tableoutput, sys, toolkit
from toolkit import IDLabel


###########################################
## data.frame / report -> python         ##
###########################################

def getcell(matrix, i,j):
    nrows = matrix.dim[0]
    return matrix[j*nrows + i]

class MatrixTable(table3.Table):
    def __init__(self, matrix):
        self.matrix = matrix
    def getColumns(self):
        ncols = self.matrix.dim[1]
        return range(ncols)
    def getRows(self):
        nrows = self.matrix.dim[0]
        return range(nrows)
    def getValue(self, row, col):
        return getcell(self.matrix, row,col)

class FrameTable(table3.Table):
    def __init__(self, frame):
        self.frame = frame
    def getColumns(self):
        return [IDLabel(*c) for c in enumerate(self.frame.colnames())]
    def getRows(self):
        return [IDLabel(*r) for r in enumerate(self.frame.rownames())]
    def getValue(self, row, col):
        return self.frame[col.id][row.id]

class Plot(object):
    def __init__(self, filename):
        if filename.startswith("file://"):
            filename = filename[7:]
        self.filename = filename
    def toHTML(self):
        bytes = open(self.filename).read()
        return toolkit.htmlImageObject(bytes)
    
class Report(object):
    def __init__(self, report):
        self.report = report
    def getResults(self):
        for element in self.report:
            if len(element)<>2:
                raise Exception("Element has %i parts (need label, obj):\n%s\n==\n%r\n---------\nReport is:\n%s\n==\n%r" % (len(element), element, element, self.report, self.report))
            label, obj = element
            if type(obj) in (str,unicode) and obj.startswith("file://"):
                obj = Plot(obj)
            yield label, obj
    def printReport(self, out=sys.stdout):
        gen = tableoutput.HTMLGenerator(rownames=True)
        for label, obj in self.getResults():
            out.write("<h2>%s</h2>" % label)
            if isinstance(obj, table3.Table):
                gen.generate(obj, out)
            elif isinstance(obj, Plot):
                out.write(obj.toHTML())
            else:
                out.write("<pre>%s</pre>" % obj)
        
    
def interpret(robj, scalar=True, recurse=True):
    #print "Interpreting %s %s" % (robj, type(robj))
    if type(robj) in (float,str,): return robj
    if isinstance(robj, robjects.RArray):
        return MatrixTable(robj)
    if isinstance(robj, robjects.RDataFrame):
        return FrameTable(robj)
    if isinstance(robj, robjects.RVector):
        if str(robj.getnames()) <> 'NULL':
            # this is a list - return key/value pairs
            func = interpret if recurse else lambda x:x
            return [(name, func(val)) for (name, val)
                    in zip(robj.getnames(), robj)]
        if scalar and len(robj) == 1:
            return robj[0]
        if scalar and len(robj) == 0:
            return None
        else:
            if recurse:
                return [interpret(o, scalar=scalar, recurse=recurse) for o in robj]
            else:
                return list(robj)
    if isinstance(robj, robjects.RObject) or isinstance(robj, robjects.RS4):
        cl = robj.rclass[0]
        if  cl == "NULL":
            return None
        if cl == "ResultList":
            return ResultList(robj)
        raise Exception("Cannot interpret %s objects with class %s" % (robj.__class__, cl))
    raise Exception("Cannot interpret %s objects" % robj.__class__)

def getReport(rfile, function, *args, **kargs):
    return Report(call(rfile, function, *args, **kargs))

def call(rfile, function, *args, **kargs):
    robjects.r.source(rfile)
    # argument magic to overcome py2.5 no keyword arg after * limitation
    int_args = {}
    for arg in ['scalar', 'recurse']:
        int_args[arg] = kargs.get(arg, True)
    interprt = kargs.get('interpret', False)
    for arg in ['scalar', 'recurse', 'interpret']:
        if arg in kargs: del kargs[arg]
    # end argument magic
        
    obj = robjects.r[function](*args, **kargs)
    if interprt:
        obj = interpret(obj, **int_args)
    return obj
    
   

###########################################
## table3.Table -> data.frame            ##
###########################################

def getFactorVector(x):
    strings = robjects.StrVector(x)
    return robjects.r.factor(strings)

VECTORS = {int : robjects.IntVector, float : robjects.FloatVector, str : getFactorVector, None : robjects.IntVector}

def table2RFrame(table):
    
    cols = rlc.ArgsDict() 
    for col in table.getColumns():
        print col
        vector = [table.getValue(row, col) for row in table.getRows()]
        types = set(map(type, vector))
        nonnull = types - set([type(None)])
        if not nonnull: func = VECTORS[int]
        elif len(nonnull) > 1: raise Exception("Column %s has more than one type: %s" % (col, types))
        else:
            t = nonnull.pop()
            func = VECTORS.get(t)
        if not func:
            print col, vector[:20]
            raise Exception("Unknown vector type: %s" % types)
        cols[str(col)] = func(vector)
    return robjects.r["data.frame"].rcall(cols.items())


if __name__ == '__main__':
    l = getReport("/home/wva/libpy/ml/r/test.r", "test", interpret=True)
    l.printReport()


