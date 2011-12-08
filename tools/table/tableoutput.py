from __future__ import with_statement
from amcat.tools import toolkit, idlabel
from amcat.tools.logging import progress
import sys, csv, StringIO, traceback, json

from amcat.tools.logging import amcatlogging;

from django.template import Template, Context

#amcatlogging.debugModule()

import logging; log = logging.getLogger(__name__)

def getTable(table, colnames=None):
    if isinstance(table, (list, tuple)):
        from amcat.tools.table import table3
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
        
def table2unicode(table, colnames=None, formats=None, useunicode=True, box=True, rownames=False, stream=None, encoding=None):
    def write(s):
        if encoding: s = s.encode(encoding)
        stream.write(s)
    returnstring = (not stream)
    if returnstring:
        stream = StringIO.StringIO()
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
            #if isinstance(col, idlabel.IDLabel) and
            if col in sortcols:
                headers.append(u"%s %s" % (str(col), SORTINDICATORS[useunicode, sortcols[col]]))
            else:
                headers.append(str(col))
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

    if rownames:
        collengths.insert(0, 15)
        headers.insert(0, "")
    write(sep(collengths, con_sep2t))
    write(line(map(formatheader, headers), collengths, con_line))
    write(sep(collengths, con_sep))
    for r in data:
        write(line(r, collengths, con_line))
    write(sep(collengths, con_sep2b))
    if returnstring:
        return stream.getvalue()


########################### table2html #######################################

class HTMLGenerator(object):
    # use some sort of templating???
    def __init__(self, tclass=None, rownames=False, attrhook=None):
        self.tclass = tclass
        self.rownames = rownames
        self.NoneString = ''
        self.attrhook = attrhook # function(header=False, row=None, col=None) --> dict of attrs

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
        self.open(stream, "tr", **self.getRowAttrs(row))
        if self.rownames: self.element(stream, str(row), "th", **self.getCellAttrs(row=row))
        for col in table.getColumns():
            try:
                val = table.getValue(row, col)
                if val is None: val = self.NoneString
                if type(val) == unicode: val = val.encode('utf-8')
                elif type(val) == float: val = "%1.3f" % val
                elif type(val) <> str: val = unicode(val).encode('utf-8')
            except Exception:
                val = '<span style="color:red" title="%s">ERROR</span>' % traceback.format_exc().replace('"', "'")
            self.element(stream, val, "td", **self.getCellAttrs(row=row, col=col))
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
        if '__skip__' in openkargs: return
        self.open(stream, element, *openargs, **openkargs)
        stream.write(contents)
        self.close(stream, element)
    def getCellAttrs(self, row=None, col=None):
        if self.attrhook: return self.attrhook(False, row, col)
        return {}
    def getRowAttrs(self, row):
        if self.attrhook: return self.attrhook(True, row, None)
        return {}
    
                       
def yieldtablerows(table):
    for row in table.getRows():
        yield [table.getValue(row, col) for col in table.getColumns()]
        

def table2html(table, colnames=None, printRowNames = True, border=True):
    table = getTable(table, colnames)
    if table.rowNamesRequired == True:
        printRowNames = True
    result = "\n<table border='1'>" if border else "\n<table>"
    result += "\n  <thead><tr>"
    if printRowNames: result += "\n    <th></th>"
    result += "%s\n  </tr></thead><tbody>" % "".join("\n    <th>%s</th>" % (col,) for col in table.getColumns())
    for row in table.getRows():
        result += "\n  <tr>"
        if printRowNames: result += "\n    <th>%s</th>" % row
        
        result += "".join("\n    <td>%s</td>" % table.getValue(row, col) for col in table.getColumns())
        result += "</tr>"
    result += "\n</tbody></table>"
    return result
    
def table2htmlDjango(table, writecolnames=True, writerownames=False):
    if table.rowNamesRequired == True:
        writerownames = True
    t = Template("""<table class="display">
        {% if writecolnames %}
        <thead>
            {% if writerownames %}
                <th></th>
            {% endif %}
            {% for header in table.getColumns %}
                <th>{{header}}</th>
            {% endfor %}
        </thead>
        {% endif %}
        <tbody>
            {% for row in table %}
                <tr>
                    {% if writerownames %}
                        <td>{{row.row}}</td>
                    {% endif %}
                    {% for col in row %}
                        <td>{{col|default_if_none:"-" }}</td>
                    {% endfor %}
                </tr>
            {% endfor %}
       </tbody>
    </table>""")
    c = Context({"table": table, 'writecolnames':writecolnames, 'writerownames':writerownames})
    return t.render(c)

####################### table2csv ###################################

def getstr(val):
    if val is None: return ""
    if type(val) == str: return val
    if type(val) == unicode: return val.encode('utf-8')
    return str(val)

"""
commented this code, since it is overwritten by following function anyway..
def table2csv(table, colnames=None, csvwriter=None, outfile=sys.stdout, writecolnames=True, writerownames=False,
              tabseparated=False, monitor=progress.NullMonitor()):
    with monitor.monitored("Exporting to CSV", 100) as pm:
        table = getTable(table, colnames)
        if csvwriter is None:
            dialect = csv.excel_tab if tabseparated else csv.excel
            csvwriter = csv.writer(outfile, dialect=dialect)
        pm.worked(5)
        cols = list(table.getColumns())
        if writecolnames == True: writecolnames = str 
        if writerownames == True: writerownames = str            
        if writecolnames:
            c = ([""] + cols) if writerownames else cols
            csvwriter.writerow(map(writecolnames, c))
        pm.worked(5)
        rows = table.getRows()
        log.debug("Starting export")
        
        with monitor.monitored("Exporting to CSV", 100, submonitorwork=90) as m:
            for i, row in enumerate(rows):
                n = table.estimateRows()
                m.workedto(100 * i / n)
                values = [writerownames(row)] if writerownames else []
                values += map(getstr, (table.getValue(row,col) for col in cols))
                csvwriter.writerow(values)
"""

def table2csv(table, colnames=None, csvwriter=None, outfile=sys.stdout, writecolnames=True, writerownames=False,
              tabseparated=False):
    table = getTable(table, colnames)
    if table.rowNamesRequired == True:
        writerownames = True
    if csvwriter is None:
        dialect = csv.excel_tab if tabseparated else csv.excel
        csvwriter = csv.writer(outfile, dialect=dialect)
    cols = list(table.getColumns())
    if writecolnames == True: writecolnames = str 
    if writerownames == True: writerownames = str            
    if writecolnames:
        c = ([""] + cols) if writerownames else cols
        csvwriter.writerow(map(writecolnames, c))
    rows = table.getRows()
    log.debug("Starting export")
    
    for row in rows:
        values = [writerownames(row)] if writerownames else []
        values += map(getstr, (table.getValue(row,col) for col in cols))
        csvwriter.writerow(values)

        
def table2json(table, colnames=None, writecolnames=True, writerownames=False):
    table = getTable(table, colnames)
    cols = list(table.getColumns())
    headersjson = []
    if writecolnames:
        c = ([""] + cols) if writerownames else cols
        headersjson.append(c)
    rows = table.getRows()
    rowsjson = []
    for row in rows:
        values = [writerownames(row)] if writerownames else []
        values += (table.getValue(row,col) for col in cols)
        rowsjson.append(values)
    return json.dumps({'headers':headersjson, 'rows':rowsjson}, default=lambda o:unicode(o), indent=2)

if __name__ == '__main__':
    t = table3.DictTable(default=0)
    t.addValue(("bla","x"), "pi,et", 3)
    t.addValue(("bla","y"), "ja\tn", 4)
    t.addValue(("bla","y"), "piet", 5)
    table2csv(t, writerownames=lambda s : "/".join(map(str, s)), tabseparated=True)
