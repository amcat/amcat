import table3, toolkit

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

def table2ascii(table, colnames=None, formats=None, useunicode=True, box=True):
    table = getTable(table, colnames)
    con_sep2t, con_sep2b, con_sep, con_line = CONNECTORS[useunicode, box]
    cols, rows = table.getColumns(), table.getRows()
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
        return fmt%val if (val is not None) else ""

    data = []
    collengths = [len(unicode(hdr)) for hdr in headers]
    for row in rows:
        data.append([])
        for i, col in enumerate(cols):
            value = cell(row, col, formats[i])
            collengths[i] = max(collengths[i], len(value))
            data[-1].append(value)
    
    result = ""
    result += sep(collengths, con_sep2t)
    result += line(headers, collengths, con_line)
    result += sep(collengths, con_sep)
    for r in data:
        result += line(r, collengths, con_line)
    result += sep(collengths, con_sep2b)
    return result


########################### table2html #######################################

def table2html(table, colnames=None):
    table = getTable(table, colnames)
    result = "\n<table border='1'>"
    result += "\n  <tr>\n    <th></th>%s\n  </tr>" % "".join("\n    <th>%s</th>" % (col,) for col in table.getColumns())
    for row in table.getRows():
        result += "\n  <tr>\n    <th>%s</th>%s\n  </tr>" % (
            row,
            "".join("\n    <td>%s</td>" % table.getValue(row, col) for col in table.getColumns())
            )
    result += "\n</table>"
    return result
