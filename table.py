# Eclipse-inspired MVC implementation of tables
#
# rows should be something that iterates over the row elements
# You may supply one or more columns that implement two functions:
#   getHeader() should return an object representing the header
#   getCell(row) should return an object representing the cell in the
#           row represented by the row element
#
# You may supply zero or more Labeler objects, who should implement
#   getLabel(object)
# For each object, each of the labelers will be called in sequence
# until a labeler returns something other than None. The returned
# value, or the original obejct if no labeler accepted the object,
# will be displayed. Returning a CellInfo object rather than a string
# might help certain display functions (ie HTML)

import colorsys, math, StringIO, csv, decimal

def simpleLabeler(func):
    def labeler(cell):
        lbl = func(cell.value)
        if lbl:
            cell.label = lbl
            return True
        return False
    return labeler

class Table(object):
    def __init__(self, rows=None):
        self.rows = rows
        self.columns = []
        self.labelers = []
        self.conf = None
        self._data = None
        self._header = None
    def addColumn(self, column, func=None):
        if func: column=Column(column, func)
        self.columns.append(column)
    def addColumns(self, columns):
        self.columns += list(columns)
    def addLabeler(self, labeler):
        self.labelers.append(labeler)
    def setCellLabel(self, cell):
        for labeler in self.labelers:
            if labeler(cell): return
        cell.label = cell.value

    def header(self):
        if self._header is None:
            self._header = TableRow(self, None)
            self._header.cells = [self.cell(col.getHeader(), True) for col in self.columns]
        return self._header

    def cell(self, c, header=False):
        if not isinstance(c, CellInfo): c = CellInfo(c, header=header)
        self.setCellLabel(c)
        return c        
    
    def data(self):
        if self._data is None:
            self._data = []
            for row in self.rows:
                r = TableRow(self, row)
                self._data.append(r)
                if self.conf.beforeRowStart: self.conf.beforeRowStart(r)
                r.cells = [self.cell(col.getCell(row)) for col in self.columns]
        return self._data

    def getCSV(self):
        if not self.conf: self.conf = CSVConf()
        outfile = StringIO.StringIO()
        w = csv.writer(outfile, self.conf.dialect)
        w.writerow(self.header().cells)
        for row in self.data():
            w.writerow([self.conf.format(x.value) for x in row.cells])
        return outfile.getvalue()

    def getHTML(self, rowLimit=2000, limitmsg="Row limit reached (%d rows)"):
        if not self.conf: self.conf = HTMLTableConf()
        clas = " class='%s' " % self.conf.tableClass if self.conf.tableClass else ""
        html = "<table%s>\n"  % clas
        html += rowHTML(self.header())
        rowCount = 0
        for row in self.data():
            rowCount += 1
            html += rowHTML(row)
            
            if rowLimit and (rowCount > rowLimit): # for performance issues
                html += '</table>'
                html += '<div class="message">%s</div>' % (limitmsg % rowLimit)
                return html
        if rowCount == 0:
            html += '<tr><td colspan="%d" class="no-data">No data found</td></tr>' % len(self.header().cells)
        html += "</table>\n"
        return html

    def colorize(self):
        min, max = None, None
        for row in self.data():
            for c in row.cells:
                if type(c.value) in (int, float):
                    if min is None or c.value < min: min=c.value
                    if max is None or c.value > max: max=c.value
        for row in self.data():
            for c in row.cells:
                v = c.value
                if type(v) in (int, float):
                    if max - min == 0: continue
                    v = float(v - min) / (max - min)
                    h = .666 + .167 * v
                    s = .5#1- v/2
                    b = 1-v/2
                    c.color = HSL2HTML(h,s,b)
                    #c.value = "%1.2f,%1.2f,%1.2f,%1.2f,%s" % (v,h,s,b,c.color)

class TableRow(object):
    def __init__(self, table, obj):
        self.table = table
        self.obj = obj
        self.cells = []
        self.labels = []
        self.text = ""
        self.data = {}
    def previous(self):
        i = self.table.data().index(self)
        if i == 0: return None
        return self.table.data()[i-1]

class TableConf(object):
    def __init__(self):
        self.beforeRowStart = None
        self.afterRowDone = None

class CSVConf(TableConf):
    def __init__(self, dialect=None, eu=True):
        TableConf.__init__(self)
        self.dialect = dialect or csv.excel()
        self.eu = eu
        if self.eu:
            self.dialect.delimiter=';'
    def format(self, x):
        if type(x) in (float, decimal.Decimal) and self.eu:
            return str(x).replace(".",",")
        if type(x) == unicode:
            x = x.encode('utf-8')
        return x
        

class HTMLTableConf(TableConf):
    def __init__(self, tableClass=None, cellClass=None, cellStyle=None, maxlen=None,rowClass=None):
        TableConf.__init__(self)
        self.tableClass = tableClass
        self.cellClass = cellClass
        self.cellStyle = cellStyle
        self.maxlen = maxlen
        self.rowClass = rowClass

class CellInfo(object):
    def __init__(self, value, clas=None, style=None, url=None, header=False, color=None):
        self.value = value
        self.clas = clas
        self.style = style
        self.url = url
        self.color = color
        self.header = header
    def getTD(self, conf):
        td = "th" if self.header else "td"
        clas = self.clas if self.clas else conf.cellClass
        style= self.style if self.style else conf.cellStyle
        clas = " class='%s' "%clas if clas else ""
        style= " style='%s' "%style if style else ""
        tdstyle = " style='background-color:%s' " % self.color if self.color else ""
        try:
            #text = unicode(str(self.label), 'latin-1')
            text = str(self.label).decode('latin-1') if type(self.label) != unicode else self.label
        except Exception, e:
            raise Exception(`self.label` + str(e))
        title = ""
        if conf.maxlen and len(text) > conf.maxlen:
            title = " title='%s'" % text
            text = text[:conf.maxlen-3] + ".."
        if self.url:
            text = "<a href='%s'%s>%s</a>" % (self.url, title, text) if self.url else self.value
            title = ""
        if style or title:
            text = "<span %s %s>%s</span>" % (style, title, text)
        return "<%s %s%s>%s</%s>" % (td, tdstyle, clas, text, td)
    def __str__(self):
        return str(self.value)

def rowHTML(row):
    conf = row.table.conf
    clas=" class='%s'" % row.data["class"] if ("class" in row.data) else ""
    row.text = "  <tr%s>%s</tr>\n" % (clas, "".join(x.getTD(conf) for x in row.cells))
    if row.obj and conf.afterRowDone:
        conf.afterRowDone(row)
    return row.text

class Column(object):
    def __init__(self, header, cellfunc):
        self.header = header
        self.cellfunc = cellfunc
    def getHeader(self):
        return self.header
    def getCell(self, row):
        return self.cellfunc(row)

if __name__ == '__main__':
    t = Table()
    t.rows = [4,5,6]
    t.addColumn(Column("x", lambda x:CellInfo(x, url="clickme")))
    t.addColumn(Column("x^2", lambda x:x*x))
    t.addColumn(Column("x^3", lambda x:x*x*x))
    print t.getHTML()
    
def f2hex(f):
    i = int(math.floor(f * 255 + .5))
    if i < 0: i = 0
    if i > 255: i = 255
    h = hex(i).split("x")[-1]
    if len(h) == 1: h = "0" + h
    return h

def HSL2HTML(h,s,l):
    rgb = colorsys.hls_to_rgb(h,l,s)
    return "#%2s%2s%2s" % tuple(f2hex(f) for f in rgb)

