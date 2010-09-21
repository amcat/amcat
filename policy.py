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


"""
Usage: python policy.py [-h]

Test whether the libpy/*.py modules comply with AmCAT policy
"""

from __future__ import with_statement
import unittest, os.path, os, sys, types
import amcatwarning, toolkit
import table3, tableoutput
import amcattest, hg


LICENSE = """###########################################################################
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
"""


def getLicenseOK(fn):
    """Check whether the file contains the L{LICENSE} note"""
    fn = getFn(fn)
    if not os.path.exists(fn): return None
    sourcecode = open(fn).read()
    return (LICENSE in sourcecode) and (sourcecode.index(LICENSE) < 100)

def getPylintScore(fn):
    """Get the pylint score of the file"""
    p = getPylint(fn, tail=2) or ""
    score = toolkit.getREGroups(r"Your code has been rated at (-?[0-9\.]+)/10", p)
    if score: return float(score)

def getPylint(fn, tail=None, format=None):
    """Get the pylint report of the file"""
    fn = getFn(fn)
    if not os.path.exists(fn): return None
    options = ""
    if format: options += "-f %s" % format 
    cmd = 'pylint --rcfile=/home/amcat/resources/pylintrc %s "%s"' % (options, fn)
    if tail: cmd += " | tail -%i" % tail
    return toolkit.execute(cmd)[0]
    
_CHECK_CHILDREN_TYPES = types.ClassType, types.TypeType
_NEED_DOCTYPES = _CHECK_CHILDREN_TYPES + (
    types.FunctionType, types.UnboundMethodType, types.MethodType)


def membersHaveDocStrings(obj, module=None):
    """Check whether all public members have a docstring"""
    if not module: module = obj.__name__
    for membername in dir(obj):
        if membername.startswith("_"): continue
        member = getattr(obj, membername)
        if getattr(member, "__module__", module) != module: continue

        if not isinstance(member, _NEED_DOCTYPES): continue
        yield membername, bool(getattr(member, '__doc__', None))
        if isinstance(member, _CHECK_CHILDREN_TYPES):
            for name, ok in membersHaveDocStrings(member, module):
                yield "%s.%s" % (membername, name), ok
                                                
def hasDocStrings(fn, returnbool=False, returnpair=True):
    """Check whether all public members of fn have a docstring

    @param fn: the (filename of the) module to check
    @param returnbool: if True, return a pair (npassed, ntotal)
      If False, yield the individual name, bool pairs
    """
    if type(fn) == str:
        if not os.path.exists(fn): return
        if fn  == __file__: return
        m = amcattest.getModule(fn)
    else:
        m = fn
    result = membersHaveDocStrings(m)
    if returnbool:
        return all(ok for (dummy, ok) in result if ok)
    elif returnpair:
        result = list(result)
        return len([ok for (dummy, ok) in result if ok]), len(result)
    return result

def getTestPath(fn):
    """Determine the 'test/test_x.py' file corresponding to fn"""
    fn2 = getFn(fn)
    #if not fn2: raise Exception([fn2, fn])
    repo = hg.getRepo(fn2)
    fn2 = fn2[len(repo)+1:]
    fn2 = "test_" + fn2.replace("/", "_")
    return os.path.join(repo, "test", fn2)
    
def getSuites(fn):
    """Get the test suites for the file fn"""
    testpath = getTestPath(fn)
    if not os.path.exists(testpath): return None
    return amcattest.getSuites(testpath)
    
def passesTest(fn):
    """Determine whether fn passes the test

    @return: a pair (npassed, ntotal)"""
    testpath = getTestPath(fn)
    if not os.path.exists(testpath): return None
    suites = amcattest.getSuites(testpath)
    t = unittest.TestResult()
    with amcatwarning.storeWarnings():
        for suite in suites:
            suite.run(t)
    nfailed = len(t.errors) + len(t.failures)
    return t.testsRun - nfailed, t.testsRun

def getFn(fn):
    """Return the filename of fn if it is a module, otherwise return fn"""
    return fn if type(fn) == str else fn.__file__

def getFilenameInRepo(fn):
    """Return the filename part of fn relative to its repo"""
    return getFn(fn)[(len(hg.getRepo(getFn(fn)))+1):]

        
    
def getColumns():
    """Get all defined policy columns (L{table3.ObjectColumn}s)"""
    return (
        table3.ObjectColumn("Repo", lambda fn : hg.getRepo(getFn(fn))),
        table3.ObjectColumn("Folder", lambda fn : os.path.dirname(getFilenameInRepo(fn))),
        table3.ObjectColumn("File", lambda fn : os.path.basename(getFn(fn))),
        table3.ObjectColumn("HG Status", lambda fn : hg.getStatus(getFn(fn))),
        table3.ObjectColumn("Last Edit", lambda fn : hg.getLastEditUser(getFn(fn))),
        table3.ObjectColumn("License?", getLicenseOK),
        table3.ObjectColumn("PyLint Score", getPylintScore),
        table3.ObjectColumn("DocString?", hasDocStrings),
        table3.ObjectColumn("Unit Test", passesTest),
        )

    
def getFiles(path=None):
    """Get all non-ignored files in the repo containing path"""
    if not path: path = __file__
    repo = hg.getRepo(path)
    for (fn, status) in hg.getRepoStatus(repo):
        if fn.endswith(".py") and status != 'I':
            yield os.path.join(repo, fn)
    

def getPolicyTable(path=None, files=None):
    """Return a L{table3.Table} of files by policy tests"""
    if not files: files = getFiles(path)
    return table3.ObjectTable(files, getColumns())

    
if __name__ == '__main__':
    if "-h" in sys.argv:
        print __doc__
        sys.exit()
    libpy = os.path.normpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    table = getPolicyTable(libpy)
    table.rows = table.rows[:4]
    table = table3.SortedTable(table, table.columns[1])
    #tableoutput.HTMLGenerator().generate(table)
    tableoutput.table2unicode(table, stream=sys.stdout, encoding="utf-8")
