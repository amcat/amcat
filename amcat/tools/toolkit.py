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
Toolkit of useful methods for AmCAT

Policy:
 - Each public function should be documented!
 - It should pass pychecker without warnings
 - We should try to make good test cases in test/test_toolkit.py

This toolkit is divided into a number of sections, please stick to
this organisation!
 - decorators
 - sequence functions
 - mapping functions
 - string functions
 - date(time) functions
 - misc functions
"""


import collections
import datetime
import itertools
import logging
import random
import re
import string
import time
import warnings

log = logging.getLogger(__name__)

###########################################################################
##                               Decorators                              ##
###########################################################################


def _deprecationwarning(msg):
    warnings.warn(DeprecationWarning(msg))


def deprecated(func, msg='Call to deprecated function %(funcname)s.'):
    """
    Decorate a function to mark deprecated

    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.

    U{http://wiki.python.org/moin/PythonDecoratorLibrary}
    """

    def new_func(*args, **kwargs):
        """Print a warning and then call the original function"""
        warnings.warn(DeprecationWarning(msg % dict(funcname=func.__name__)),
                      stacklevel=2)
        return func(*args, **kwargs)

    new_func.__name__ = func.__name__
    new_func.__doc__ = ("B{Deprecated: %s}" %
                        (msg % dict(funcname=func.__name__))
                        + (func.__doc__ or "").replace("@", "\@").replace("L{", "l{"))
    new_func.__dict__.update(func.__dict__)
    return new_func


def wrapped(wrapper_function, *wrapper_args, **wrapper_kargs):
    """
    Decorator to wrap the inner function with an arbitrary function
    """

    def inner(func):
        def innermost(*args, **kargs):
            try:
                result = func(*args, **kargs)
            except Exception:
                log.exception("Error on calling wrapped {func.__name__}(args={args!r}, kargs={kargs!r})"
                              .format(**locals()))
                raise
            try:
                return wrapper_function(result, *wrapper_args, **wrapper_kargs)
            except Exception:
                log.exception("Error on calling wrapper function {wrapper_function.__name__}"
                              "({result!r}, *{wrapper_args}, **{wrapper_kargs!r})".format(**locals()))
                raise

        return innermost

    return inner


###########################################################################
##                     Sequence functions                                ##
###########################################################################
def head(seq):
    """Return the first element in seq"""
    return next(iter(seq))

def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks."""
    if n < 1:
        raise ValueError("Size of {} invalid for grouper() / splitlist().".format(n))
    return itertools.zip_longest(fillvalue=fillvalue, *([iter(iterable)] * n))


def splitlist(iterable, itemsperbatch=100):
    """Split a list into smaller lists. Uses no fillvalue, as opposed to grouper()."""
    _fillvalue = object()
    for group in grouper(iterable, itemsperbatch, _fillvalue):
        yield [e for e in group if e is not _fillvalue]


###########################################################################
##                      Mapping functions                                ##
###########################################################################

class multidict(collections.defaultdict):
    """A dictionary of key : set pairs"""

    def __init__(self, seq, ltype=set):
        """Create a new multidict from a seq of key,value pairs (with duplicate keys).

        @type seq: iterable

        @type ltype: set, list
        @param ltype: default dict key-value"""
        collections.defaultdict.__init__(self, ltype)

        add = self.add if ltype is set else self.append
        if seq:
            for kv in seq:
                if kv:
                    add(*kv)

    def add(self, key, value):
        self[key].add(value)

    def append(self, key, value):
        self[key].append(value)


###########################################################################
##                         String functions                              ##
###########################################################################

ACCENTS_MAP = {'a': '\xe0\xe1\xe2\xe3\xe4\xe5',
               'c': '\xe7',
               'e': '\xe9\xe8\xea\xeb',
               'i': '\xec\xed\xee\xef',
               'n': '\xf1',
               'o': '\xf3\xf2\xf4\xf6\xf8',
               'u': '\xf9\xfa\xfb\xfc',
               'y': '\xfd\xff',

               'A': '\xc0\xc1\xc2\xc3\xc4\xc5',
               'C': '\xc7',
               'E': '\xc8\xc9\xca\xcb',
               'I': '\xcc\xcd\xce\xcf',
               'N': '\xd1',
               'O': '\xd2\xd3\xd4\xd5\xd6\xd8',
               'U': '\xd9\xda\xdb\xdc',
               'Y': '\xdd',

               's': '\u0161\u015f',
               'ss': '\xdf',
               'ae': '\xe6',
               'AE': '\xc6',


               '?': '\xbf',
               "'": '\x91\x92\x82\u2018\u2019\u201a\u201b\xab\xbb\xb0',
               '"': '\x93\x94\x84\u201c\u201d\u201e\u201f\xa8',
               '-': '\x96\x97\u2010\u2011\u2012\u2013\u2014\u2015',
               '|': '\xa6',
               '...': '\x85\u2026\u2025',
               '.': '\u2024',
               ' ': '\x0c\xa0',
               '\n': '\r',
               "2": '\xb2',
               "3": '\xb3',
               #u"(c)" : u'\xa9',
}

REV_ACCENTS_MAP = {}
for to, from_characters in ACCENTS_MAP.items():
    for from_character in from_characters:
        if from_character in REV_ACCENTS_MAP:
            raise ValueError("Character {} occured twice on right-hand side".format(from_character))
        REV_ACCENTS_MAP[from_character] = to

"""Map of unaccented : accented pairs.

The values (accented) are strings where each character is an accented
version of the corresponding key (unaccented). The key can be of length>1
if appropriate (e.g. german sz, ellipsis)"""


def strip_accents(s):
    """Replace accented characters in s by their unaccepted equivalents

    @param s: the string to strip accents from.
    @return: a str string containing the translated input
    """
    return "".join(REV_ACCENTS_MAP.get(c, c) for c in s)


def random_alphanum(size=10):
    return ''.join([random.choice(string.ascii_letters + string.digits) for i in range(size)])


###########################################################################
##                     Date(time) functions                              ##
###########################################################################

MONTHNAMES = (('jan', 'janv', 'ener', 'gennaio'),
              ('feb', 'fevr', 'feve', 'f\xe9vrier'),
              ('mar', 'mrt', 'maa', 'mar', 'm\xe4rz', 'maerz'),
              ('apr', 'avri', 'abri'),
              ('may', 'mai', 'mei', 'mayo', 'maggio', 'm\xe4rz'),
              ('jun', 'juin', 'giugno'),
              ('jul', 'juil', 'luglio'),
              ('aug', 'aout', 'agos', 'ao\xfbt'),
              ('sep', 'setem', 'settembre'),
              ('oct', 'okt', 'out', 'ottobre'),
              ('nov'),
              ('dec', 'dez', 'dici', 'dicembre', 'd\xe9cembre'))
"""Tuple of 12 tuples containing month name (prefixes)"""


class _DateFormat(object):
    """Format definition for parsing dates"""

    def __init__(self, expr, yeargroup=3, monthgroup=2, daygroup=1,
                 monthisname=False, swapamerican=False):
        self.expr = re.compile(expr, re.UNICODE)
        self.yeargroup = yeargroup
        self.monthgroup = monthgroup
        self.daygroup = daygroup
        self.monthisname = monthisname
        self.swapamerican = swapamerican

    def readDate(self, date, american=False):
        """Read the given date, producing a y,m,d tuple"""
        match = re.search(self.expr, date)
        if not match: return
        y, m, d = [match.group(x)
                   for x in (self.yeargroup, self.monthgroup, self.daygroup)]
        if self.monthisname:
            m = _monthnr(m)
            if not m: return
        y, m, d = map(int, (y, m, d))
        # 2-digit year logic:
        if y < 40:
            y += 2000
        elif y < 100:
            y += 1900
        # dmy vs mdy
        if american and self.swapamerican:
            m, d = d, m
        return y, m, d


_DATEFORMATS = (
    _DateFormat("(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})", 1, 2, 3),
    _DateFormat("(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})", 3, 2, 1, swapamerican=True),
    _DateFormat("(\w+),?\s+(\d{1,2})\s*,?\s+(\d{4})", 3, 1, 2, True),
    _DateFormat("(\w+)\s+(\d{1,2})\s*,?\s+(\d{4})", 3, 1, 2, True),
    _DateFormat("(\d{1,2})(?:\w\w?|\.)?\s+(\w*)\s+(\d{4})", 3, 2, 1, True),
    _DateFormat("\w*?,?\s*(\d{1,2})\s+(\w+)\s+(\d{4})", 3, 2, 1, True),
    _DateFormat("(\d{1,2})\.?\s+(\w*)\s+(\d{4})", 3, 2, 1, True),
    _DateFormat("(\d{1,2})[- ](\w+)[- ](\d{2,4})", 3, 2, 1, True),
    _DateFormat("(\w+) (\d{1,2}), (\d{4})", 3, 1, 2, True),
    _DateFormat("(\d{1,2})(\w{3})(\d{4})", 3, 2, 1, True),
    _DateFormat("(\d{1,2})[-/](\d{1,2})[-/](\d{2})", 3, 2, 1, swapamerican=True),

)


def _monthnr(monthname):
    """Try to get a month number corresponding to the month
    name (prefix) in monthname"""
    for i, names in enumerate(MONTHNAMES):
        for name in names:
            if monthname.lower().startswith(name.lower()):
                return i + 1


def read_date(string, lax=False, rejectPre1970=False, american=False):
    """Try to read a date(time) string with unknown format

    Attempt a number of date formats to read str

    @param string: the date string to read
    @param lax: if True, return None if no match was found instead of
      raising an error
    @param rejectPre1970: if True, reject dates before 1970 (to catch
      problems with incorrect parses)
    @param american: prefer MDY over DMY
    @return: a \C{datetime.datetime} object
    """
    if string is None: return None
    try:
        datestr = string

        time = None
        if ':' in datestr:
            m = re.match(r"(.*?)(\d+:[\d:]+)(\s+PM\b)?(?= \+\d{4} (\d{4}))?", datestr)
            if m:
                datestr, timestr, pm, year = m.groups()
                if year:
                    # HACK: allow (twitter) to specify year AFTER the timezone indicator (???) 
                    datestr += year
                try:
                    time = tuple(map(int, timestr.split(":")))
                except ValueError:
                    time = []
                if len(time) == 3:
                    pass
                elif len(time) == 2:
                    time = time + (0,)
                elif lax:
                    time = None
                else:
                    raise ValueError("Could not parse time part "
                                     + "('%s') of datetime string '%s'"
                                     % (timestr, string))
                if pm and time[0] != 12: time = (time[0] + 12, ) + time[1:]
        for df in _DATEFORMATS:
            date = df.readDate(datestr, american=american)
            if date: break

        datestr = datestr.lower()
        if not date:
            # For 'October 20, 2010'
            for i, prefixes in enumerate(MONTHNAMES):
                if datestr.startswith(prefixes):
                    month_plus_day, year = datestr.split(',')
                    day = month_plus_day.split(' ')[1]
                    date = int(year), i + 1, int(day)

        if not date:
            # For '22 November 2006 Wednesday 10:23 AM (Central European Time)'
            s = datestr.split(' ')
            if len(s) > 2:
                for i, prefixes in enumerate(MONTHNAMES):
                    if s[1].startswith(prefixes):
                        try:
                            date = int(s[2]), i + 1, int(s[0])
                        except:
                            pass
                        finally:
                            break

        if not date:
            if lax: return
            raise ValueError("Could not parse datetime string '%s'" % (string))

        if date[0] < 1970 and rejectPre1970:
            if lax: return None
            raise ValueError("Rejecting datetime string %s -> %s"
                             % (string, date))

        if not time: time = (0, 0, 0)
        return datetime.datetime(*(date + time))
    except Exception as e:
        import traceback

        trace = traceback.format_exc()
        #warn("Exception on reading datetime %s:\n%s\n%s" % (string, e, trace))
        if lax:
            return None
        else:
            raise




def to_datetime(date):
    """Convert datetime.date object to datetime.datetime"""
    return datetime.datetime(year=date.year, month=date.month, day=date.day)


###########################################################################
##                         Misc. functions                               ##
###########################################################################
# Please try to keep this one clean...

class Timer:
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start

