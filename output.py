import toolkit, operator

class Table:

    def __init__(self):
        self.rows = []
        self.currentRow = []
        self.header = []
        self.metaheader = {}

    def newRow(self):
        self.rows.append(self.currentRow)
        self.currentRow = []

    def addValue(self, *value):
        if len(value)==1 and toolkit.isSequence(value[0], True): value = value[0]
        for v in value:
            self.currentRow.append(v)

    def sort(self, kolomnr=0, reverse=False):
        self.rows.sort(key=operator.itemgetter(kolomnr), reverse=reverse)
        
    def addHeader(self, *header):
        if len(header)==1 and toolkit.isSequence(header[0], True): header = header[0]
        for h in header:
            self.header.append(h)

    def addMetaHeader(self, fr, span, text):
        self.metaheader[fr] = (span, text)

    def addRow(self, *value):
        self.addValue(value)
        self.newRow()

    def toText(self):
        result = ""
        if self.header:
            result += toolkit.output(self.header, delimiter="\t| ", floatformat="%1.2f") + "\n"
            result += "-" + "+".join(["-------"] * len(self.header)) + "\n"
        for row in self.rows:
            result += toolkit.output(row, delimiter="\t| ", floatformat="%1.2f") + "\n"
        return result



    def toHTML(self):
        
        result = "<table border=1>\n"
        o = toolkit.Output(pre='    <th>',post='</th>\n',delimiter='')
        if self.metaheader and self.header:
            result += "  <tr>\n"
            i = 0
            while i < len(self.header):
                if i in self.metaheader:
                    result += "    <th colspan=%s>%s</th>\n" % self.metaheader[i]
                    i += self.metaheader[i][0]
                else:
                    result += "    <th border=0></th>\n"
                    i += 1
            result += "  </tr>\n"
            
        if self.header:
            result += "  <tr>\n%s  </tr>\n" % o.output(self.header)
            
        o = toolkit.Output(pre='    <td>',post='</td>\n',delimiter='')
        for row in self.rows:
            result += "  <tr>\n%s  </tr>\n" % o.output(row)
        return result + "</table>\n"

    
                                                        
    def toCSV(self, asList = False, desc = None):
        result = ""
        if asList:
            for row in self.rows:
                header = self.header or ["col%s" % x for x in range(len(row) - 1)]
                if desc: result += "%s;" % desc
                for name, val in zip(header, row[1:]):
                    result += toolkit.output([row[0], name, val], delimiter=";") + "\n"
        else:
            if self.header:
                result += toolkit.output(self.header, delimiter=";") + "\n"
            for row in self.rows:
                result += toolkit.output([quoteCSV(x) for x in row], delimiter=";") + "\n"
        return result


def quoteCSV(s):
    if not toolkit.isString(s): return s
    if ';' in s:
        s = s.replace('"', '""')
        return '"%s"' % s
    return s
