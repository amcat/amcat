
import sys
import csv
import logging

from io import StringIO

log = logging.getLogger(__name__)


def getTable(table, colnames=None):
    if isinstance(table, (list, tuple)):
        from amcat.tools.table import table3
        table = table3.ListTable(table, colnames)
    return table


# ###################### table2ascii / unicode ##########################

CONNECTORS = {  # (unicode, box) : (sep2t, sep2b, sep, line)
                (True, False): (None, None, " \u2500\u253c ", " \u2502 "),
                (True, True): ("\u2554\u2550\u2564\u2557", "\u255a\u2550\u2567\u255d", "\u255f\u2500\u253c\u2562",
                               "\u2551\u2502\u2551"),
                (False, True): ("+=++", "+=++", "+-++", "|||"),
                (False, False): (None, None, " -+ ", " | "),
}
SORTINDICATORS = {
    (True, True): "\u25b2",
    (True, False): "\u25bc",
    (False, True): "^",
    (False, False): "v",
}


def sep(collengths, con="+-++"):
    if con is None: return ""
    l, c, m, r = con
    return (((l + c) if l != " " else "")
            + (c + m + c).join(c * i for i in collengths)
            + ((c + r) if r != " " else "") + "\n")


def line(values, collengths, con="|||"):
    l, m, r = con
    return (((l + " ") if l != " " else "")
            + (" " + m + " ").join(("%%-%is" % length) % (value,) for (length, value) in zip(collengths, values))
            + " " + r + "\n")


def table2ascii(table, colnames=None, formats=None, useunicode=False, box=False):
    return table2unicode(table, colnames, formats, useunicode, box)


def table2unicode(table, colnames=None, formats=None, useunicode=True, box=True, rownames=False, stream=None,
                  encoding=None):
    def write(s):
        if encoding: s = s.encode(encoding)
        stream.write(s)

    returnstring = (not stream)
    if returnstring:
        stream = StringIO()
    table = getTable(table, colnames)
    con_sep2t, con_sep2b, con_sep, con_line = CONNECTORS[useunicode, box]
    cols, rows = table.getColumns(), table.getRows()
    if type(cols) not in (list, tuple): cols = list(cols)
    if formats is None: formats = ["%s"] * len(cols)
    headers = cols
    sortcols = None
    try:
        sortcols = dict(table.sort)
    except AttributeError:
        pass
    if sortcols:
        headers = []
        for col in cols:
            # if isinstance(col, idlabel.IDLabel) and
            if col in sortcols:
                headers.append("%s %s" % (str(col), SORTINDICATORS[useunicode, sortcols[col]]))
            else:
                headers.append(str(col))

    def cell(row, col, fmt):
        val = table.getValue(row, col)
        if type(val) == str: val = val.decode('latin-1')
        if not useunicode and type(val) == str: val = val.encode('ascii', 'replace')
        try:
            val = fmt % (val,) if (val is not None) else ""
            return val
        except Exception as e:
            return str(e)

    def formatheader(h):
        if not h: return h
        if type(h) in (list, tuple, set): return ",".join(map(str, h))
        return str(h)


    data = []
    collengths = [len(str(hdr)) for hdr in headers]
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


####################### table2csv ###################################

def table2csv(table, colnames=None, csvwriter=None, outfile=sys.stdout, writecolnames=True, writerownames=False,
              tabseparated=False):
    table = getTable(table, colnames)

    writerownames = table.rowNamesRequired or writerownames

    if csvwriter is None:
        dialect = csv.excel_tab if tabseparated else csv.excel
        csvwriter = csv.writer(outfile, dialect=dialect)

    cols = list(table.getColumns())

    if writecolnames:
        _columns = ([""] + cols) if writerownames else cols
        csvwriter.writerow([str(c) for c in _columns])

    log.debug("Starting export")

    for row in table.getRows():
        values = [str(row)] if writerownames else []
        values += [str(table.getValue(row, col)) or "" for col in cols]
        csvwriter.writerow(values)


