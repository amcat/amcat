###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################
import subprocess
import tempfile
import re
import datetime
import collections
import os.path
import logging

log = logging.getLogger(__name__)

# Do not let PSPP documentation get in the way of writing proper PSPP input :)
SPSS_TYPES = {
    int: " (F8.0)",
    str: " (A255)",
    float: " (DOT9.2)",
    datetime.datetime: " (DATETIME)"
}

SPSS_SERIALIZERS = {
    type(None): lambda n: "",
    str: lambda s: '"{}"'.format(s.replace('"', "'")[:255-3]),
    datetime.datetime: lambda d: d.strftime("%d-%b-%Y-%H:%M:%S").upper()
}

PSPP_VERSION_RE = re.compile(b"pspp \(GNU PSPP\) (\d+)\.(\d+).(\d+)")
PSPPVersion = collections.namedtuple("PSPPVersion", ["major", "minor", "micro"])

def get_pspp_version() -> PSPPVersion:
    try:
        process = subprocess.Popen(["pspp", "--version"], stdout=subprocess.PIPE)
    except FileNotFoundError:
        raise FileNotFoundError("Could not execute pspp. Is it installed?")

    stdout, _ = process.communicate()
    for line in stdout.splitlines():
        match = PSPP_VERSION_RE.match(line)
        if match:
            return PSPPVersion(*map(int, match.groups()))

    raise PSPPError("Could not find version of installed pspp.")


def clean(s, max_length=255):
    s = s.encode('ascii', 'replace').decode("ascii")
    s = re.sub("[^\w, :-]", "", s)
    return s[:max_length-3].strip()


def get_var_name(col, seen):
    fn = str(col).replace(" ", "_")
    fn = fn.replace("-", "_")
    fn = re.sub('[^a-zA-Z_]+', '', fn)
    fn = re.sub('^_+', '', fn)
    fn = fn[:16]
    if fn in seen:
        for i in range(400):
            if "%s_%i" % (fn, i) not in seen:
                fn = "%s_%i" % (fn, i)
                break
    seen.add(fn)
    return fn


def _getVarDef(varname, vartype):
    return "%s%s" % (varname, SPSS_TYPES[vartype])


def serialize_spss_value(typ, value, default=lambda o: str(o)):
    return SPSS_SERIALIZERS.get(typ, default)(value)


def table2spss(t, saveas):
    cols = list(t.getColumns())
    seen = set()
    varnames = {col: get_var_name(col, seen) for col in cols}
    vartypes = {col: t.getColumnType(col) or str for col in cols}

    vardefs = " ".join(_getVarDef(varnames[col], vartypes[col]) for col in cols)

    log.debug("Writing var list")
    log.info(vardefs)
    yield "DATA LIST LIST\n / %s .\nBEGIN DATA.\n" % vardefs

    log.debug("Writing data")
    valuelabels = collections.defaultdict(dict)  # col : id : label
    for row in t.getRows():
        for i, col in enumerate(cols):
            if i:
                yield ","
            typ = vartypes[col]
            value = t.getValue(row, col)
            yield serialize_spss_value(typ, value)
        yield "\n"
    yield "END DATA.\n"

    # Print table for debugging purposes. Does not influence the file generated below.
    yield "list.\n"

    log.debug("Writing var labels")
    varlabels = " / ".join("%s '%s'" % (varnames[c], clean(str(c), 55)) for c in cols)
    yield "VARIABLE LABELS %s.\n" % varlabels

    log.debug("Writing value labels")
    for c in cols:
        vl = valuelabels[c]
        if vl:
            yield "VALUE LABELS %s\n" % varnames[c]
            for id, lbl in sorted(vl.items()):
                yield "  %i  '%s'\n" % (id, clean(lbl, 250))
            yield ".\n"

    log.debug("Saving file")
    yield "SAVE OUTFILE='%s'.\n" % saveas


class PSPPError(Exception):
    pass


def table2sav(t):
    _, filename = tempfile.mkstemp(suffix=".save", prefix="table-")

    log.debug("Check if we've got the right version of PSPP installed")
    version = get_pspp_version()
    if version < PSPPVersion(0, 8, 5):
        raise PSPPVersion("Expected pspp>=8.5.0, but found {}".format(version))

    log.debug("Starting PSPP")
    pspp = subprocess.Popen(
        ["pspp", "-b"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    log.debug("Generating SPSS code..")
    pspp_code = "".join(table2spss(t, filename))

    log.debug("Encodign PSPP code as ASCII..")
    pspp_code = pspp_code.encode("utf-8")

    log.debug("Sending code to pspp..")
    stdout, stderr = pspp.communicate(input=pspp_code)

    stdout = stdout.decode("utf-8")
    stderr = stderr.decode("utf-8")

    log.debug("PSPP stderr: %s" % stderr)
    log.debug("PSPP stdout: %s" % stdout)

    stderr = stderr.replace('pspp: error creating "pspp.jnl": Permission denied', '')
    stdout = stdout.replace('pspp: ascii: opening output file "pspp.list": Permission denied', '')

    if stderr.strip():
        raise PSPPError(stderr)
    if "error:" in stdout.lower():
        raise PSPPError("PSPP Exited with error: \n\n%s" % stdout)
    if not os.path.exists(filename):
        raise PSPPError("PSPP Exited without errors, but file was not saved.\n\nOut=%r\n\nErr=%r" % (stdout, stderr))
    return filename
