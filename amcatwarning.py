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
Extension to the python warnings platform for AmCAT to allow user-aimed
warnings

A number of warning levels are defined
 - Information
 - Problem
 - Critical

"""

from __future__ import with_statement
import warnings, time, threading, contextlib, sys

START = time.time()

USE_CURSES = True
"""Set to False to suppress use of curses for warning"""
COLOURS = ['red', 'yellow', 'purple', 'green', 'blue']
"""Available colour levels in order of warning severity"""

_COLOURS = dict(zip(COLOURS, [(31, 1), (33, 2), (35, 2), (32, 2), (34, 2)]))
# 31,1 --> colour = 31, boldness = 1 (=bold, 2=regular)

class AmcatWarning(Warning):
    """Base class for AmCAT Warning message.

    Subclasses should create a class attribute severity (int)"""
    def __init__(self, msg):
        # need to change msg in place because the object is lost before
        # calling showwarning!
        thread = (threading.currentThread().getName()
                  if threading.currentThread().getName() != 'MainThread'
                  else '')
        msg = "%8.4f %s%s" % (time.time() - START, thread, msg)
        Warning.__init__(self, msg)
    def warn(self):
        """Convenience method to call warnings.warn(self)"""
        warnings.warn(self, stacklevel=2)
        

class Information(AmcatWarning):
    """Class to use for Information messages""" 
    severity = 4
class Problem(AmcatWarning):
    """Class to use for Problem messages""" 
    severity = 2
class Error(AmcatWarning):
    """Class to use for Error messages""" 
    severity = 0
    
def coloured(colour, text):
    """
    Return a 'curses' string coloured with the given colour

    @type colour: str
    @param colour: the colour to use, see the global COLOURS list
    @param text: the text to colour
    """
    c, bold = _COLOURS.get(colour, 0)
    return u'\033[%s;%sm%s\033[m' % (c, bold, text)

#override default formatwarning to supply AmcatWarnings with their own format
def amcat_formatwarning(message, category, filename, lineno, *args, **kargs):
    """Custom formatting to use severity for colour"""
    if not issubclass(category, AmcatWarning):
        return warnings.formatwarning(message, category,
                                      filename, lineno, *args, **kargs)        
    msg = "%-30s %s\n" % ("%s:%s" % (filename, lineno), message)
    if USE_CURSES: msg = coloured(COLOURS[category.severity], msg)
    return msg

def _showwarning(message, category, filename, lineno, file=sys.stderr,
                 line=None):
    """Custom showwarning that uses amcat_formatwarning"""
    file.write(amcat_formatwarning(message, category, filename, lineno))
warnings.showwarning = _showwarning
    
# def getCaller(depth=2): # [checktoolkit.py: unused]
#     import inspect
#     stack = inspect.stack()
#     try:
#         if len(stack) <= depth:
#             return None, None, None
#         frame = stack[depth][0]
#         try:
#             return inspect.getframeinfo(frame)[:3]
#         finally:
#             del frame
#     finally:
#         del stack

@contextlib.contextmanager
def storeWarnings():
    """Context Manager to store warnings rather than let them be printed

    yields the list that will be used to append warnings as
    (message, category, filename, lineno, file, line) tuples that can
    be passed to warnings.formatwarning.

    Example usage:

    >>> with storeWarnings() as w:
    ...    #code that might raise a warning
    ... print "\n".join(warnings.formatwarning(*args) for args in w)
    """
    storedwarnings = []
    _showwarning = warnings.showwarning
    warnings.showwarning = lambda *args : storedwarnings.append(args)
    try:
        yield storedwarnings
    finally:
        warnings.showwarning = _showwarning    


if __name__ == '__main__':
    Information("bla1").warn()
    with storeWarnings() as w:
        Information("bla2").warn()
    Information("bla3").warn()
    print "----------"
    print "".join(warnings.formatwarning(*args) for args in w)

