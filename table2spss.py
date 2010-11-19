import dbtoolkit, codingjob, table3, toolkit
import sys, csv
import re
import datetime
from idlabel import IDLabel
import collections
import os.path

def clean(s, maxchars=None):
    if type(s) == str: s = s.decode('latin-1')
    if type(s) == unicode: s = s.encode('ascii','replace')
    else: s = str(s)
    s= re.sub("[^\w, ]","",str(s).strip())
    if maxchars and len(s) > maxchars: s = s[:maxchars-1]
    return s

def getSPSSFormat(type):
    if type == int: return " (F8.0)"
    if issubclass(type, IDLabel): return " (F8.0)"
    if type == float: return " (F8.3)"
    if type == str: return " (A255)"
    if type == datetime.datetime: return " (date10)"
    raise Exception("Unknown type: %s" % type)

def table2spss(t, writer=sys.stdout, saveas=None):
    cols = t.getColumns()

    # resolve duplicate field names - the hard way
    seen = set()
    for c in cols:
        if c.fieldname in seen:
            f = c.fieldname
            for i in xrange(400):
                if "%s_%i" % (f, i) not in seen:
                    c.fieldname = "%s_%i" % (f, i)
                    break
        seen.add(c.fieldname)
            
    
    vardefs = " ".join("%s%s" % (c.fieldname, getSPSSFormat(c.fieldtype))
                       for c in cols)
    toolkit.ticker.warn("Writing var list")
    writer.write("DATA LIST LIST\n / %s .\nBEGIN DATA.\n" % vardefs)

    toolkit.ticker.warn("Writing data")
    valuelabels = collections.defaultdict(dict) # col : id : label
    for row in t.getRows():
        for i, col in enumerate(cols):
            if i: writer.write(",")
            val = t.getValue(row, col)
            if val and col.fieldtype == IDLabel:
                valuelabels[col][val.id] = val.label
                val = val.id
            if val and col.fieldtype == str:
                val = '"%s"' % clean(val)
            if val and col.fieldtype == datetime.datetime:
                val = val.strftime("%d/%m/%Y")
            val = "" if val is None else str(val)
            writer.write(val)
        writer.write("\n")
    writer.write("END DATA.\n")

    toolkit.ticker.warn("Writing var labels")
    varlabels = " / ".join("%s '%s'" % (c.fieldname, clean(c.label, 55)) for c in cols)
    writer.write("VARIABLE LABELS %s.\n" % varlabels)

    toolkit.ticker.warn("Writing value labels")
    for c in cols:
        vl = valuelabels[c]
        if vl:
            writer.write("VALUE LABELS %s\n" % c.fieldname)
            for id, lbl in sorted(vl.iteritems()):
                writer.write("  %i  '%s'\n" % (id, clean(lbl, 250)))
            writer.write(".\n")
    if saveas:
        toolkit.ticker.warn("Saving file")
        writer.write("SAVE OUTFILE='%s'.\n" % saveas)

class EchoWriter(object):
    def __init__(self, writer):
        self.writer = writer
    def write(self, bytes):
        sys.stdout.write(bytes)
        self.writer.write(bytes)
        
def table2sav(t, filename=None):
    if filename is None: filename = toolkit.tempfilename(suffix=".sav",prefix="table-")
    pspp = toolkit.executepipe("pspp -p")
    writer = pspp.next()
    #writer = EchoWriter(writer)
    table2spss(t, writer=writer, saveas=filename)
    out, err = pspp.next()
    err = err.replace('pspp: error creating "pspp.jnl": Permission denied','')
    err = err.replace('pspp: ascii: opening output file "pspp.list": Permission denied','')
    if err.strip():
        raise Exception(err)
    if "error:" in out.lower():
        raise Exception("PSPP Exited with error: \n\n%s"  % out)
    if not os.path.exists(filename):
        raise Exception("PSPP Exited without errors, but file was not saved.\n\nOut=%r\n\nErr=%r"% (out, err))
    return filename

if __name__ == '__main__':
    db = dbtoolkit.amcatDB()
    cj = codingjob.CodingJob(db, 4534)
    t = table3.ObjectTable(rows=codingjob.getCodedSentencesFromCodingjobs([cj]),
                           columns=map(SPSSFieldColumn, cj.unitSchema.fields))
    
    print table2sav(t)
    

    
