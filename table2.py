from toolkit import isnull
import StringIO
import chartlib, base64
import dot
import toolkit, os


TEMPDIR = os.path.dirname(__file__) + '/../www-tmp'
WWWTEMPDIR = 'tmp'

class Header(object):
    def __init__(self, label, headerfunc):
        self.label = label
        self.headerfunc = headerfunc
    def getLabel(self):
        return self.label
    def getHeader(self, obj):
        return self.headerfunc(obj)
    def __str__(self):
        return "Header(%s, ..)" % self.label
    def __repr__(self):
        return self.__str__()
    
class SimpleHeader(Header):
    def __init__(self, label):
        Header.__init__(self, label, str)

class Table(object):
    def __init__(self, columns = None, rows = None, cellfunc = None, colheaders = None, rowheaders = None, cellheader = None):
        self.columns    = isnull(columns, []) # data objects representing columns
        self.rows       = isnull(rows, [])    # data objects representing row
        self.cellfunc   = isnull(cellfunc, lambda row, col : "%s/%s" % (row, col)) # map col/row onto value`
        self.colheaders = isnull(colheaders, []) # Header objects
        self.rowheaders = isnull(rowheaders, []) # Header objects
        self.coltotals  = [] # Header objects
        self.rowtotals  = [] # Header objects
        self.cellheader = cellheader
    def getValue(self, row, column):
        return self.cellfunc(row, column)
    def toHTML(self, *args, **kargs):
        w = StringIO.StringIO()
        HTMLGenerator(w, *args, **kargs).toHTML(self)
        return w.getvalue()
    def toHTMLGraphObject(self, *args, **kargs):
        return ChartGenerator(*args, **kargs).generateHTMLObject(self)
    def toGraphTempFile(self, *args, **kargs):
        return ChartGenerator(*args, **kargs).generateTempFile(self)
    def toHTMLNetworkObject(self, *args,  **kargs):
        return NetworkGenerator(*args, **kargs).generateHTMLObject(self, openaspdf=kargs.get('openaspdf'))
    def toNetworkPDF(self, *args, **kargs):
        return NetworkGenerator(*args, **kargs).generatePDF(self)
    def transpose(self):
        self.rows, self.columns = self.columns, self.rows
        self.colheaders, self.rowheaders = self.rowheaders, self.colheaders
        x = self.cellfunc
        self.cellfunc = lambda a,b : x(b,a)

class ObjectColumn(object):
    def __init__(self, header, cellfunc):
        self.header = header
        self.cellfunc = cellfunc
    def getHeader(self):
        return self.header
    def getCell(self, row):
        return self.cellfunc(row)
    
class ObjectTable(Table):
    def __init__(self, rows = None, columns = None):
        self.rows = rows or []
        self.columns = columns or []
        self.rowheaders = []
        self.colheaders = [Header("", lambda x:x.getHeader())]
        self.cellfunc = lambda row, col : col.getCell(row)
        self.coltotals = []
        self.rowtotals = []
    def addColumn(self, col, func=None):
        if type(col) in (str, unicode) and func:
            col = ObjectColumn(col, func)
        self.columns.append(col)
    def getHTML(self, *args, **kargs):
        return self.toHTML(*args, **kargs)
        
class DataTable(Table):
    """
    Convenience subclass of Table that creates a dict to hold the cell values,
    and adds column and row objects as needed
    """
    def __init__(self, default=None):
        Table.__init__(self)
        self.data = {}
        self.default = default
        self.columns = SimpleOrderedSet()
        self.rows = SimpleOrderedSet()
        self.cellfunc =  lambda row, col: self.data.get((row, col), default)
    def addValue(self,row, col, value):
        self.data[row, col] = value
        self.columns.add(col)
        self.rows.add(row)

class SimpleOrderedSet(list):
    def __init__(self):
        list.__init__(self)
        self.set = set()
    def add(self, object):
        if object in self.set: return
        self.set.add(object)
        self.append(object)

class ChartGenerator(object):
    def __init__(self, type=None, valfunc = None, tempfile=False, libOptions={}):
        self.type = type or 'line'
        self.valfunc = valfunc
        self.tempfile = tempfile
        self.libOptions = libOptions
    def getVal(self, val):
        if self.valfunc:
            return self.valfunc(val)
        else:
            return float(val or 0)
    def chartData(self, table):
        # columns -> labels
        labels = [
            " - ".join(str(ch.getHeader(c)) for ch in table.colheaders)
            for c in table.columns]
        # rows -> series, so rows+cells -> data dict
        data = {}
        for r in table.rows:
            key = " - ".join(str(rh.getHeader(r)) for rh in table.rowheaders)
            data[key] = [self.getVal(table.cellfunc(r,c)) for c in table.columns]
        return data, labels

    def generateTempFile(self, table, tempDir="/tmp"):
        data, labels = self.chartData(table)
        fn, map = chartlib.chart(self.type, data, labels, tempDir)
        return fn, map
    def generateHTMLObject(self, table):
        if 'title' not in self.libOptions: self.libOptions['title'] = table.cellheader or ''
        png, map = chartlib.chart(self.type, *self.chartData(table), **self.libOptions)
        png = chartlib.cropData(png)
        if self.tempfile:
            return tmpimg(png), map
        else:
            data = base64.b64encode(png)
            return ("<object type='image/png' data='data:image/png;base64,%s'></object>" % data), map
        
class NetworkGenerator(object):
    def __init__(self, qwfunc=None, colorfunc = None, tempfile=False, linkpdf = False, **kargs):
        self.qwfunc = qwfunc
        self.colorfunc = colorfunc
        self.tempfile = tempfile
        self.linkpdf = linkpdf
    def getVal(self, val):
        if self.qwfunc:
            return self.qwfunc(val)
        if type(val) in (tuple, list):
            return val
        else:
            return None, val
        
    def getLabel(self, headers, object):
        return " - ".join(str(header.getHeader(object)) for header in headers) 
        headers = table.rowheaders if row else table.col
    def generateDot(self, table):
        g = dot.Graph()
        for r in table.rows:
            rlbl = self.getLabel(table.rowheaders, r)
            for c in table.columns:
                clbl = self.getLabel(table.colheaders, c)
                val = table.cellfunc(r,c)
                if val is None: continue
                q,w = self.getVal(val)
                if w is None: continue
                if type(w) == long: w = int(w)
                if type(w) not in (int, float):
                    raise Exception([w, type(w)])
                e = g.addEdge(clbl,rlbl)
                e.weight = w
                if q is not None: e.sign = q
                if self.colorfunc:
                    e.color = self.colorfunc(w, q)

        g.normalizeWeights()
                
        return g
    def generateHTMLObject(self, table, openaspdf=True):
        g = self.generateDot(table)
        if self.tempfile:
            png = g.getImage(format='png')
            html = tmpimg(png)
            if self.linkpdf:
                pdf = self.generatePDF(table)
                if openaspdf:
                    html = tmpimg(pdf, ".pdf", "Open as PDF") + "<br/>" + html
            return html
        else:
            return g.getHTMLObject()
    def generatePDF(self, table):
        g = self.generateDot(table)
        img = g.getImage(format='ps')
        img = toolkit.ps2pdf(img)
        return img

def tmpimg(png, suffix=".png", ahref=None):
    fn = toolkit.tempfilename(suffix=suffix, prefix="figure-", tempdir=TEMPDIR)            
    f = open(fn, 'wb')
    f.write(png)
    f.close()
    if ahref is not None:
        return "<a href='%s'>%s</a>" % (fn.replace(TEMPDIR, WWWTEMPDIR) , ahref)
    else:
        return "<img src='%s'></img>" % fn.replace(TEMPDIR, WWWTEMPDIR) 

class HTMLGenerator(object):
    def __init__(self, writer, tdfunc=None, thfunc=None, trclassfunc=None, tableclass='data-table'):
        self.writer = writer
        self.tdfunc = tdfunc
        self.thfunc = thfunc
        self.trclassfunc = trclassfunc
        self.tableclass = tableclass
    
    def toHTML(self, table):
        self.startTable()
        # column headers
        for i in range(len(table.rowheaders)):
            cls = "headcol"
            if i == 0: cls += "first"
            if i == len(table.rowheaders) - 1: cls += "last"
            self.col(cls)
        for i in range(len(table.columns)):
            cls = "datacol"
            if i == 0: cls += "first"
            if i == len(table.columns) - 1: cls += "last"
            self.col(clas=cls)
            
        for i, ch in enumerate(table.colheaders):
            cls = "headrow"
            if i == 0: cls += "first"
            if i == len(table.colheaders) - 1: cls += "last"
            self.startRow(clas=cls)
            for j, rh in enumerate(table.rowheaders):
                header = []
                if i == len(table.colheaders) -1: # last header row, print row header title
                    if rh.getLabel() is not None:
                        header.append(rh.getLabel())
                if j == len(table.rowheaders) -1: # last header col, print col header title
                    if ch.getLabel() is not None:
                        header.append(ch.getLabel())
                header = "&nbsp;\&nbsp;".join(header)
                self.headercell(header, clas="colrow")
            cheads = map(ch.getHeader, table.columns)
            for j, (chead, span) in enumerate(zip(cheads, spans(cheads))):
                if span is None: continue
                self.headercell(chead, colspan=span, clas="col")
            self.endRow()
        # normal rows, first cache all row headers and spans
        rowheaders = map(lambda rh : map(rh.getHeader, table.rows), table.rowheaders)
        rowheaders = map(lambda rh : zip(rh, spans(rh)), rowheaders)
        for i, r in enumerate(table.rows):
            cls = None
            if self.trclassfunc: cls = self.trclassfunc(r)
            self.startRow(clas=cls)
            for rh in rowheaders:
                rhead, span = rh[i]
                if span is not None:
                    self.headercell(rhead, rowspan=span, clas="row")
            for c in table.columns:
                self.cell(table.cellfunc(r, c))
            self.endRow()

        for i, ct in enumerate(table.coltotals):
            cls = "totalrow"
            if i == 0: cls += "first"
            if i == len(table.coltotals): cls += "last"
            self.startRow(clas=cls)
            for j, rh in enumerate(table.rowheaders):
                if j == 0:
                    self.headercell(ct.getLabel(), clas="totalrowheader")
                else:
                    self.headercell("", clas="totalrowempty")
            for c in table.columns:
                self.headercell(ct.getHeader(c), clas="totalrowcell")
            self.endRow()
        self.endTable()
        
    def startRow(self, clas=None):
        s = " class='%s'" % clas if clas else ""
        self.writer.write(" <tr%s>\n" % s)
    def col(self, clas):
        self.writer.write(" <col class='%s'></col>" % clas)
    def startTable(self):
        attrstr = " class='%s'" % self.tableclass if self.tableclass else ""
        self.writer.write("<table%s>\n" % attrstr)
    def endRow(self):
        self.writer.write(" </tr>\n")
    def endTable(self):
        self.writer.write("</table>\n")
    def headercell(self, value, **attr):
        if "clas" in attr:
            attr["class"] = attr["clas"]
            del attr["clas"]
        if self.thfunc:
            th = self.thfunc(value, attr)
        else:
            th = element("th", value, **attr)
        self.writer.write(th)            
    def cell(self, value):
        if self.tdfunc:
            td = self.tdfunc(value)
        else:
            td = element("td", value)
        self.writer.write(td)


class Value(object):
    def __init__(self, value, direction=None, url=None, direction2=None, value2=None, lineval=None, istotal=False, nospan=True, suffix=None):
        self.value = value
        self.direction = direction
        self.direction2 = direction2
        self.relative = None
        self.url = url
        self.value2 = value2
        self.lineval = lineval or value
        self.istotal=istotal
        self.nospan = nospan
        self.suffix = suffix
    def __str__(self):
        return str(self.value)
        
def element(tag, content, **attrs):

    if isinstance(content, Value):
        text = str(content.value)
        if content.url:
            text = "<a href='%s'>%s</a>" % (content.url, text)
    else:
        if type(content) == unicode:
            text= content.encode('ascii', 'replace')
        else:
            text = str(content)
        
    if attrs:
        astr = " " + attr2str(attrs)
    else:
        astr = ""
    return "<%s%s>%s</%s>\n" % (tag, astr, text, tag)
                

        
def attr2str(attr):
    return "".join(' %s="%s"' % kv for kv in attr.items())
                

def getTestDataTable():
    t = DataTable()
    t.addValue("pvda", "jan", 1)
    t.addValue("pvda","maa", 3)
    t.addValue("vvd","jan", 4)
    t.addValue("vvd","feb", 2)
    t.addValue("cda","feb", 1)
    t.addValue("cda","maa", 5)
    t.addValue("cda","jan", 2)
    agg = {"pvda" : "opp", "vvd" : "opp", "cda" : "coa"}
    t.rowheaders = [Header("cat", lambda x : agg[x]),
                    SimpleHeader("party")]
    t.colheaders = [SimpleHeader("month")]
    return t

def getTestTable():
    t = Table()
    data = {}
    data["pvda","jan"] = 1
    data["pvda","maa"] = 3
    data["vvd","jan"] = 4
    data["vvd","feb"] = 2
    data["cda","feb"] = 1
    data["cda","maa"] = 5
    data["cda","jan"] = 2

    agg = {"pvda" : "opp", "vvd" : "opp", "cda" : "coa"}

    t.rowheaders = [Header("cat", lambda x : agg[x]),
                    SimpleHeader("party")]
    t.colheaders = [SimpleHeader("month")]
    
    t.rows = "pvda","vvd","cda"
    t.columns = list(set(x[1] for x in data.keys()))
    t.cellfunc = lambda r,c: data.get((r,c))
    return t 

def spans(seq):
    """
    return a new list, containing the number of times
    the corresponding element occurred after the current,
    and None if it is a repeat occurrence itself
    e.g.: spans([1,5,5,5,2,1,1]) -> [1,3,None,None,1,2,None]
    """
    if len(seq) == 0: return []
    if len(seq) == 1: return [1]
    old = seq[0]
    span = 1
    result = []
    for e in list(seq)[1:] + [seq]:
        if e <> old or (isinstance(e, Value) and e.nospan):
            result += [span] + [None] * (span -1)
            old = e
            span = 1
        else:
            span += 1
    return result

def testHTMLTable():
    print """<html><head><style>
             tr {background: #aaf}
             td {background: #ccf}
             </style></head><body>"""
    t = getTestDataTable()
    print t.toHTML()

def testGraph():
    t = getTestDataTable()
    t.transpose()
    print ChartGenerator().generateHTMLObject(t)

def testObjectTable():
    t = ObjectTable()
    t.rows = [4,5,6]
    t.addColumn(ObjectColumn("x", lambda x : Value(x, url="bla.html")))
    t.addColumn(ObjectColumn("x^2", lambda x:x*x))
    t.addColumn(ObjectColumn("x^3", lambda x:x*x*x))
    print t.getHTML()       
    
if __name__ == '__main__':
    #testGraph()
    testObjectTable()
    
