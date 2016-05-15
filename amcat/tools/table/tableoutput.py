import io
import sys
import csv
import logging

from io import StringIO

log = logging.getLogger(__name__)


# ###################### table2ascii / unicode ##########################

CONNECTORS = {  # box : (sep2t, sep2b, sep, line)
                False: (None, None, " \u2500\u253c ", " \u2502 "),
                True: ("\u2554\u2550\u2564\u2557", "\u255a\u2550\u2567\u255d", "\u255f\u2500\u253c\u2562",
                               "\u2551\u2502\u2551"),
}
SORTINDICATORS = {
    True: "\u25b2",
    False: "\u25bc",
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


def table2unicode(table, box=True, rownames=False, stream=None):
    return_string = not stream
    if not stream:
        stream = StringIO()

    con_sep2t, con_sep2b, con_sep, con_line = CONNECTORS[box]

    cols = list(table.get_columns())
    rows = list(table.get_rows())

    headers = cols

    try:
        sortcols = dict(table.sort)
    except AttributeError:
        pass
    else:
        headers = []
        for col in cols:
            if col in sortcols:
                headers.append("%s %s" % (str(col), SORTINDICATORS[sortcols[col]]))
            else:
                headers.append(str(col))

    def cell(row, col):
        value = table.get_value(row, col)
        return str(value) if value is not None else ""

    def formatheader(h):
        if not h:
            return h

        if isinstance(h, (list, tuple, set)):
            return ",".join(map(str, h))

        return str(h)

    data = []
    collengths = [len(str(hdr)) for hdr in headers]
    for row in rows:
        data.append([])
        if rownames:
            data[-1].append(formatheader(row))
        for i, col in enumerate(cols):
            value = cell(row, col)
            collengths[i] = max(collengths[i], len(value))
            data[-1].append(value)

    if rownames:
        collengths.insert(0, 15)
        headers.insert(0, "")
    stream.write(sep(collengths, con_sep2t))
    stream.write(line(map(formatheader, headers), collengths, con_line))
    stream.write(sep(collengths, con_sep))
    for r in data:
        stream.write(line(r, collengths, con_line))
    stream.write(sep(collengths, con_sep2b))

    if return_string:
        return stream.getvalue()


####################### table2csv ###################################

def table2csv(table, csvwriter=None, outfile=sys.stdout, writecolnames=True, writerownames=False,
              tabseparated=False):

    writerownames = table.rowNamesRequired or writerownames

    if csvwriter is None:
        dialect = csv.excel_tab if tabseparated else csv.excel
        csvwriter = csv.writer(outfile, dialect=dialect)

    cols = list(table.get_columns())

    if writecolnames:
        _columns = ([""] + cols) if writerownames else cols
        csvwriter.writerow([str(c) for c in _columns])

    log.debug("Starting export")

    for row in table.get_rows():
        values = [str(row)] if writerownames else []
        values += [str(table.get_value(row, col)) or "" for col in cols]
        csvwriter.writerow(values)

    return outfile
