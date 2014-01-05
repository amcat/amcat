#from amcat.models.coding import codingjob
from amcat.tools.table import table3
from amcat.tools import toolkit, idlabel
#from amcat.tools.cachable import cachable
from amcat.tools import amcatlogging


import sys, csv
import re
import datetime
import collections
import os.path
import logging; log = logging.getLogger(__name__)

amcatlogging.debugModule()

def clean(s, maxchars=None):
    if type(s) == str: s = s.decode('latin-1')
    if type(s) == unicode: s = s.encode('ascii','replace')
    else: s = str(s)
    s= re.sub("[^\w, :-]","",str(s).strip())
    if maxchars and len(s) > maxchars: s = s[:maxchars-1]
    return s

def getSPSSFormat(type):
    log.debug("Determining format of %s" % type)
    if type == int: return " (F8.0)"
    if issubclass(type, idlabel.IDLabel): return " (F8.0)"
    #if issubclass(type, cachable.Cachable): return " (F8.0)"
    if type == float: return " (F8.3)"
    if type == str: return " (A255)"
    if type == datetime.datetime: return " (date10)"
    raise Exception("Unknown type: %s" % type)

def getVarName(col, seen):
    fn = str(col).replace(" ","_")
    fn = fn.replace("-","_")
    fn = re.sub('[^a-zA-Z_]+', '', fn)
    fn = re.sub('^_+', '', fn)
    if fn in seen:
        for i in xrange(400):
            if "%s_%i" % (fn, i) not in seen:
                fn = "%s_%i" % (fn, i)
                break
    seen.add(fn)
    return fn
    
def _getVarDef(varname, vartype):
    """Remove duplicates and spaces from field names"""
    vardef = "%s%s" % (varname, getSPSSFormat(vartype))
    return vardef

def table2spss(t, writer=sys.stdout, saveas=None):
    cols = list(t.getColumns())
    seen = set()
    varnames = {col : getVarName(col, seen) for col in cols}
    vartypes = {col : t.getColumnType(col) or str for col in cols}
    
    vardefs = " ".join(_getVarDef(varnames[col],vartypes[col]) for col in cols)

    log.debug("Writing var list")
    log.info(vardefs)
    writer.write("DATA LIST LIST\n / %s .\nBEGIN DATA.\n" % vardefs)


    log.debug("Writing data")
    valuelabels = collections.defaultdict(dict) # col : id : label
    for row in t.getRows():
        for i, col in enumerate(cols):
            if i: writer.write(",")
            typ = vartypes[col]
            val = t.getValue(row, col)
            oval = val
            #if val and issubclass(col.fieldtype, (idlabel.IDLabel, )):
            #    if type(val) == int:
            #        valuelabels[col][val] = "?%i" % val
             #   else:
            #        valuelabels[col][val.id] = val.label
            #        val = val.id
            if val and typ == str:
                val = '"%s"' % clean(val)
            if val and typ == datetime.datetime:
                val = val.strftime("%d/%m/%Y")
            val = "" if val is None else str(val)
            writer.write(val)
            #log.debug("Wrote %r --> %s" % (oval, val))
        writer.write("\n")
    writer.write("END DATA.\n")

    log.debug("Writing var labels")
    varlabels = " / ".join("%s '%s'" % (varnames[c], clean(unicode(c), 55)) for c in cols)
    writer.write("VARIABLE LABELS %s.\n" % varlabels)

    log.debug("Writing value labels")
    for c in cols:
        vl = valuelabels[c]
        if vl:
            writer.write("VALUE LABELS %s\n" % varnames[c])
            for id, lbl in sorted(vl.iteritems()):
                writer.write("  %i  '%s'\n" % (id, clean(lbl, 250)))
            writer.write(".\n")
    if saveas:
        log.debug("Saving file")
        writer.write("SAVE OUTFILE='%s'.\n" % saveas)

class EchoWriter(object):
    def __init__(self, writer):
        self.writer = writer
        fn = toolkit.tempfilename(".sps","data")
        self.log = open(fn, "w")
        log.warn("Writing spss commands to %s" % fn)
        
    def write(self, bytes):
        self.log.write(bytes)
        self.writer.write(bytes)
        
def table2sav(t, filename=None):
    if filename is None: filename = toolkit.tempfilename(suffix=".sav",prefix="table-")

    log.debug("Creating SPSS syntax")
    #import StringIO
    #writer = StringIO.StringIO()
    #table2spss(t, writer=writer, saveas=filename, monitor=monitor.submonitor(80))
    #sps = writer.getvalue()
    #log.debug("Wrote syntax:\n%s\n" % (sps))

    log.debug("Executing PSPP")
    pspp = toolkit.executepipe("pspp -b")
    writer = pspp.next()
    writer = EchoWriter(writer)
    log.debug("Creating SPS script and sending to PSPP")
    table2spss(t, writer=writer, saveas=filename)
    log.debug("Closing PSPP")
    out, err = pspp.next()
    log.debug("PSPPP err: %s" % err)
    log.debug("PSPPP out: %s" % out)
    err = err.replace('pspp: error creating "pspp.jnl": Permission denied','')
    err = err.replace('pspp: ascii: opening output file "pspp.list": Permission denied','')
    if err.strip():
        raise Exception(err)
    if "error:" in out.lower():
        raise Exception("PSPP Exited with error: \n\n%s"  % out)
    if not os.path.exists(filename):
        raise Exception("PSPP Exited without errors, but file was not saved.\n\nOut=%r\n\nErr=%r"% (out, err))
    return filename

