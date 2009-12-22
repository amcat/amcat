import table3, toolkit

def getTable(table, colnames=None):
    if not isinstance(table, table3.Table):
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
def line(values, formats, collengths, con="|||"):
    l, m, r = con
    return (((l+" ") if l <> " " else "")
            +(" "+m+" ").join(("%%-%is" % length) % (fmt % value) for (length, fmt, value) in zip(collengths, formats, values))
            +" " + r + "\n")   

def table2ascii(table, colnames=None, formats=None, useunicode=True, box=True):
    table = getTable(table, colnames)
    con_sep2t, con_sep2b, con_sep, con_line = CONNECTORS[useunicode, box]
    cols, rows = table.getColumns(), table.getRows()
    hdrformats = [u"%s"] * len(cols)
    if formats is None: formats = hdrformats
    headers = cols
    if isinstance(table, table3.SortedTable):
        headers = []
        sortcols = dict(table.sort)
        for col in cols:
            if isinstance(col, toolkit.IDLabel) and col in sortcols:
                headers.append(u"%s %s" % (col.label, SORTINDICATORS[useunicode, sortcols[col]]))
            else:
                headers.append(col.label)
    collengths = [max([len(fmt % table.getValue(r,c)) for r in rows] + [len(unicode(hdr))]) for (fmt, c, hdr) in zip(formats, cols, headers)]

    
    result = ""
    result += sep(collengths, con_sep2t)
    result += line(headers, hdrformats, collengths, con_line)
    result += sep(collengths, con_sep)
    for r in rows:
        result += line(map(lambda c : table.getValue(r,c), cols), formats, collengths, con_line)
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
