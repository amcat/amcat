import table3, toolkit, sys, csv

def getTable(table, colnames=None):
    if isinstance(table, (list, tuple)):
        table = table3.ListTable(table, colnames)
    return table


####################### table2ascii / unicode ##########################

CONNECTORS = { # (unicode, box) : (sep2t, sep2b, sep, line)
    (True, False) : (None,None, u" \u2500\u253c ", u" \u2502 "),
    (True, True) : (u"\u2554\u2550\u2564\u2557",u"\u255a\u2550\u2567\u255d", u"\u255f\u2500\u253c\u2562", u"\u2551\u2502\u2551"),
    (False, True) : ("+=++", "+=++", "+-++", "|||"),
    (False, False) : (None,None, " -+ ", " | "),
    }
SORTINDICATORS = {
    (True, True) : u"\u25b2",
    (True, False) : u"\u25bc",
    (False, True) : "^",
    (False, False) : "v",
    }


def sep(collengths, con = "+-++"):
    if con is None: return ""
    l,c,m,r = con
    return (((l+c) if l <> " " else "")
            +(c+m+c).join(c*i for i in collengths)
            +((c+r) if r <> " " else "")+"\n")
def line(values, collengths, con="|||"):
    l, m, r = con
    return (((l+" ") if l <> " " else "")
            +(" "+m+" ").join(("%%-%is" % length) % (value,) for (length, value) in zip(collengths, values))
            +" " + r + "\n")   

def printTable(table):
    table = getTable(table)
    cols = table.getColumns()
    for r in table.getRows():
        print toolkit.join([table.getValue(r,c) for c in cols])

def table2ascii(table, colnames=None, formats=None, useunicode=False, box=False):
    return table2unicode(table, colnames, formats, useunicode, box)
        
def table2unicode(table, colnames=None, formats=None, useunicode=True, box=True, rownames=False):
    table = getTable(table, colnames)
    con_sep2t, con_sep2b, con_sep, con_line = CONNECTORS[useunicode, box]
    cols, rows = table.getColumns(), table.getRows()
    if type(cols) not in (list, tuple): cols = list(cols)
    if formats is None: formats = [u"%s"] * len(cols)
    headers = cols
    sortcols = None
    try: sortcols = dict(table.sort)
    except AttributeError: pass
    if sortcols:
        headers = []
        for col in cols:
            if isinstance(col, toolkit.IDLabel) and col in sortcols:
                headers.append(u"%s %s" % (col.label, SORTINDICATORS[useunicode, sortcols[col]]))
            else:
                headers.append(col.label)
    def cell(row, col, fmt):
        val = table.getValue(row, col)
        if type(val) == str: val = val.decode('latin-1')
        if not useunicode and type(val) == unicode: val = val.encode('ascii' , 'replace')
        try:
            val = fmt%(val,) if (val is not None) else ""
            return val
        except Exception, e:
            return str(e)
    def formatheader(h):
        if not h: return h
        if type(h) in (list, tuple, set): return ",".join(map(unicode, h))
        return unicode(h)
            

    data = []
    collengths = [len(unicode(hdr)) for hdr in headers]
    for row in rows:
        data.append([])
        if rownames:
            data[-1].append(formatheader(row))
        for i, col in enumerate(cols):
            value = cell(row, col, formats[i])
            collengths[i] = max(collengths[i], len(value))
            data[-1].append(value)

    result = u""
    if rownames:
        collengths.insert(0, 15)
        headers.insert(0, "")
    result += sep(collengths, con_sep2t)
    result += line(map(formatheader, headers), collengths, con_line)
    result += sep(collengths, con_sep)
    for r in data:
        result += line(r, collengths, con_line)
    result += sep(collengths, con_sep2b)
    return result


########################### table2html #######################################

class HTMLGenerator(object):
    # use some sort of templating???
    def __init__(self, tclass=None, rownames=False):
        self.tclass = tclass
        self.rownames = rownames

    def generate(self, table, stream=sys.stdout):
        self.startTable(table, stream)
        self.generateHeader(table, stream)
        for row in table.getRows():
            self.generateContent(table, stream, row)
        self.endTable(table, stream)

    def generateHeader(self, table, stream):
        self.open(stream, "tr")
        if self.rownames: self.element(stream, "", "th")
        for col in table.getColumns():
            self.element(stream, str(col), "th")
        self.close(stream, "tr")
    def generateContent(self, table, stream, row):
        self.open(stream, "tr")
        if self.rownames: self.element(stream, str(row), "th")
        for col in table.getColumns():
            val = table.getValue(row, col)
            if val is None: val = ""
            if type(val) == unicode: val = val.encode('utf-8')
            elif type(val) == float: val = "%1.3f" % val
            elif type(val) <> str: val = unicode(val).encode('utf-8')

            self.element(stream, val, "td")
        self.close(stream, "tr")
    def startTable(self, table, stream):
        self.open(stream, "table", self.tclass)
    def endTable(self, table, stream):
        self.close(stream, "table")
    def open(self, stream, element, classname=None, **attrs):
        if classname: attrs["class"] = classname
        stream.write("<%s %s>" % (
            element, " ".join("%s='%s'" % kv for kv in attrs.iteritems())))
    def close(self, stream, element):
        stream.write("</%s>\n" % element)
    def element(self, stream, contents, element, *openargs, **openkargs):
        self.open(stream, element, *openargs, **openkargs)
        stream.write(contents)
        self.close(stream, element)

        

def table2html(table, colnames=None, printRowNames = True):
    table = getTable(table, colnames)
    result = "\n<table border='1'>"
    result += "\n  <tr>"
    if printRowNames: result += "\n    <th></th>"
    result += "%s\n  </tr>" % "".join("\n    <th>%s</th>" % (col,) for col in table.getColumns())
    for row in table.getRows():
        result += "\n  <tr>"
        if printRowNames: result += "\n    <th>%s</th>" % row
        
        result += "".join("\n    <td>%s</td>" % table.getValue(row, col) for col in table.getColumns())
        result += "</tr>"
    result += "\n</table>"
    return result

####################### table2csv ###################################

def getstr(val):
    if val is None: return ""
    if type(val) == str: return val
    if type(val) == unicode: return val.encode('utf-8')
    return str(val)

def table2csv(table, colnames=None, csvwriter=None, outfile=sys.stdout, writecolnames=True, writerownames=False):
    table = getTable(table, colnames)
    if csvwriter is None: csvwriter = csv.writer(outfile)
    cols = list(table.getColumns())
    if writecolnames == True: writecolnames = str 
    if writerownames == True: writerownames = str            
    if writecolnames:
        c = [""] + cols if writerownames else cols
        csvwriter.writerow(map(writecolnames, c))
    for row in table.getRows():
        values = [writerownames(row)] if writerownames else []
        values += map(getstr, (table.getValue(row,col) for col in cols))
        csvwriter.writerow(values)


if __name__ == '__main__':
    t = table3.DictTable(default=0)
    t.addValue(("bla","x"), "piet", 3)
    t.addValue(("bla","y"), "jan", 4)
    t.addValue(("bla","y"), "piet", 5)
    table2csv(t, writerownames=lambda s : "/".join(map(str, s)))
