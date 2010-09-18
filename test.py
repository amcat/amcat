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
Usage: python test.py [-w] [-v] [-h]

Runner for the test_*.py modules in libpy/test

If run from the command line, will import all modules in the
same directory as the script, find TestCases, load them,
and then run all tests.

Options:
  -h : show this message and exit
  -w : show warnings generated in the test cases
  -v : verbose
"""

from __future__ import with_statement
import unittest, os.path, os, inspect, sys
import amcatwarning, warnings



def getModule(fn):
    """Import the module from filename

    Splits the filename into path/module.py, adds path to
    sys.path (if necessary), and imports and returns module"""
    if not os.path.exists(fn): return
    path, name = os.path.split(fn)
    if path not in sys.path: sys.path.append(path)
    #raise Exception([fn, path, name, sys.path])
    return __import__(name[:-3])


def getTestCases(fn):
    """Yield all unitTest.TestCase classes from the module at fn"""
    #if type(fn) != str: raise Exception(repr(fn))
    if type(fn) == str:
        if not os.path.exists(fn): return
        m = getModule(fn)
    else:
        m = fn
    if not m: return
    for v in m.__dict__.values():
        if inspect.isclass(v) and issubclass(v, unittest.TestCase):
            yield v

def getSuites(fn):
    """Yield test suites from the testcases in fn"""
    for case in getTestCases(fn):
        yield unittest.TestLoader().loadTestsFromTestCase(case)

if __name__ == '__main__':
    if "-h" in sys.argv:
        print __doc__
        sys.exit()
    testdir = os.path.join(os.getcwd(), os.path.dirname(__file__), "test")
    suites = []
    for fn in os.listdir(testdir):
        if fn.endswith(".py"):
            for suite in getSuites(os.path.join(testdir, fn)):
                suites.append(suite)

    suite = unittest.TestSuite(suites)

    with amcatwarning.storeWarnings() as w:
        verbosity = 2 if "-v" in sys.argv else 1
        unittest.TextTestRunner(verbosity=2).run(suite)

    if w:
        if "-w" in sys.argv:
            print "\n---------\nWarnings:\n"
            print "".join(warnings.formatwarning(*args) for args in w)
        else:
            print "\nNote: %i Warning(s) have been raised."
            print "Run with -w to see the warnings" % len(w)
        
