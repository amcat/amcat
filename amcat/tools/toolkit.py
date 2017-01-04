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
 - Should not depend on any module outside to 2.7+ standard library
 - Each public function should be documented!
 - It should pass pychecker without warnings
 - We should try to make good test cases in test/test_toolkit.py

This toolkit is divided into a number of sections, please stick to
this organisation!
 - decorators
 - sequence functions
 - mapping functions
 - string/unicode functions
 - date(time) functions
 - process handling and external processes
 - type checking
 - misc functions
"""

from __future__ import unicode_literals, print_function, absolute_import
from functools import partial
import time
import warnings
import random
import types
import datetime
import re
import collections
import threading
import subprocess
import base64
import logging
import string
from django.core.serializers.json import DjangoJSONEncoder

from collections import OrderedDict, Callable
import itertools

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


def to_list(func):
    """
    This decorator puts the result of a (generator) function in a list.
    """
    return wrapped(list)(func)


###########################################################################
##                     Sequence functions                                ##
###########################################################################


def join(seq, sep="\t", fmt="%s", none=''):
    """Join a list of arbitrary objects into a string

    Augments the builtin ''.join() by not requiring string arguments
    Note: in most cases csv.writer makes more sense.
    @param seq: The sequence to join
    @param sep: The separator to use
    @param fmt: The format to apply to each element of seq
    @param none: A string to use for None values
    """

    def joinformat(elem, fmt, none):
        """fmt%elem with handling for none, unicode"""
        if elem is None: return none
        if type(elem) == unicode:
            elem = elem.encode('latin-1', 'replace')
        return fmt % elem

    return sep.join([joinformat(x, fmt, none) for x in seq])


def head(seq):
    """Return the first element in seq"""
    return next(iter(seq))


def totuple(v):
    """Function to convert `value` to a tuple."""
    if v is None:
        return ()
    elif type(v) in (str, unicode, int, long):
        return v,
    return v


def idlist(idcolumn):
    """Function to convert a idcolumn value to a list.

    An __idcolumn__ may be a str or tuple. This function
    removes the necessity to check as it always returns
    the latter.

    @type idcolumn: tuple, str or None
    @param idcolumn: value to convert to a tuple"""
    if not idcolumn: return ()

    if type(idcolumn) in (str, unicode):
        return (idcolumn,)

    raise TypeError("%s-like objects not supported" % repr(type(idcolumn)))


def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks."""
    if n < 1:
        raise ValueError("Size of {} invalid for grouper() / splitlist().".format(n))
    return itertools.izip_longest(fillvalue=fillvalue, *([iter(iterable)] * n))


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


class DefaultOrderedDict(OrderedDict):
    """http://stackoverflow.com/a/6190500/478503"""
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
            not isinstance(default_factory, Callable)):
            raise TypeError('First argument must be callable')
        OrderedDict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    def __repr__(self, **kwargs):
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
                                        OrderedDict.__repr__(self))


###########################################################################
##                   String/Unicode functions                            ##
###########################################################################

ACCENTS_MAP = {u'a': u'\xe0\xe1\xe2\xe3\xe4\xe5',
               u'c': u'\xe7',
               u'e': u'\xe9\xe8\xea\xeb',
               u'i': u'\xec\xed\xee\xef',
               u'n': u'\xf1',
               u'o': u'\xf3\xf2\xf4\xf6\xf8',
               u'u': u'\xf9\xfa\xfb\xfc',
               u'y': u'\xfd\xff',

               u'A': u'\xc0\xc1\xc2\xc3\xc4\xc5',
               u'C': u'\xc7',
               u'E': u'\xc8\xc9\xca\xcb',
               u'I': u'\xcc\xcd\xce\xcf',
               u'N': u'\xd1',
               u'O': u'\xd2\xd3\xd4\xd5\xd6\xd8',
               u'U': u'\xd9\xda\xdb\xdc',
               u'Y': u'\xdd\xdf',

               u's': u'\u0161\u015f',
               u'ss': u'\xdf',
               u'ae': u'\xe6',
               u'AE': u'\xc6',


               u'?': u'\xbf',
               u"'": u'\x91\x92\x82\u2018\u2019\u201a\u201b\xab\xbb\xb0',
               u'"': u'\x93\x94\x84\u201c\u201d\u201e\u201f\xa8',
               u'-': u'\x96\x97\u2010\u2011\u2012\u2013\u2014\u2015',
               u'|': u'\xa6',
               u'...': u'\x85\u2026\u2025',
               u'.': u'\u2024',
               u' ': u'\x0c\xa0',
               u'\n': u'\r',
               u"2": u'\xb2',
               u"3": u'\xb3',
               #u"(c)" : u'\xa9',
}
"""Map of unaccented : accented pairs.

The values (accented) are strings where each character is an accented
version of the corresponding key (unaccented). The key can be of length>1
if appropriate (e.g. german sz, ellipsis)"""


def stripAccents(s, usemap=ACCENTS_MAP, latin1=False):
    """Replace accented characters in s by their unaccepted equivalents

    @param s: the string to strip accents from. If it is not a unicode object
      it is first converted using L{unicode}C{(.., 'latin-1')}
    @param usemap: an optional translation map to use
    @return: a unicode string containing the translated input
    """
    #TODO: This is probably not very efficient! Creating a reverse map and
    #Iterating the input while building the output would be better...
    if not s: return s
    if type(s) != unicode: s = unicode(s, "latin-1")
    for key, val in usemap.items():
        for trg in val:
            if latin1 and val.encode('latin-1', 'replace').decode('latin-1') == val:
                continue

            s = s.replace(trg, key)
    return s


def random_alphanum(size=10):
    return ''.join([random.choice(string.letters + string.digits) for i in range(size)])


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
              ('aug', 'aout', 'agos', u'ao\xfbt'),
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
                if pm and time[0] < 12: time = (time[0] + 12, ) + time[1:]
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
    except Exception, e:
        import traceback

        trace = traceback.format_exc()
        #warn("Exception on reading datetime %s:\n%s\n%s" % (string, e, trace))
        if lax:
            return None
        else:
            raise


readDate = read_date


def writeDate(datetime, lenient=False):
    """Convenience method for writeDateTime(time=False)"""
    return writeDateTime(datetime, lenient=lenient, time=False)


def _writePrior1900(dt, year, seconds, time):
    """strftime doesn't work for dates prior to 1900. When found in
    writeDateTime this function is called to 'manually' write
    the date."""
    date = ''
    if year: date += "%s-" % dt.year
    date += "%0.2i-%0.2i" % (dt.month, dt.day)
    if time: date += " %0.2i:%0.2i" % (dt.hour, dt.minute)

    if seconds:
        return date + ':%0.2i' % dt.second
    return date


def writeDateTime(datetimeObj, lenient=False, year=True, seconds=True, time=True):
    """Return the datetime (stlib or mx) as ISOFormat string.

    @param datetimeObj: the datetime (mx.DateTime or stlib datetime) to convert
    @param lenient: if True, return None if datetime is None and silently
      return strings unmodified rather than raise an Exception
    @param year: if True, include the year of the date
    @param seconds: if True, include the seconds in the time part
    @param time: if False, print only the date part"""
    #Note: use strftime for mx and datetime compatability
    if lenient and ((datetimeObj is None)
                    or type(datetimeObj) in types.StringTypes):
        return datetimeObj

    if datetimeObj.year < 1900:
        return _writePrior1900(datetimeObj, year, seconds, time)

    format = "%Y-%m-%d" if year else "%m-%d"
    if time:
        format += " %H:%M:%S" if seconds else " %H:%M"
    return datetimeObj.strftime(format)


def to_datetime(date):
    """Convert datetime.date object to datetime.datetime"""
    return datetime.datetime(year=date.year, month=date.month, day=date.day)


def dateToInterval(date, interval):
    """returns the interval as string, such as 2002-04.
    Supported intervals: day, week, month, quarter, year"""
    if interval == 'day':
        return date.strftime('%Y-%m-%d')
    elif interval == 'week':
        return date.strftime('%Y-%W')
    elif interval == 'month':
        return date.strftime('%Y-%m')
    elif interval == 'quarter':
        return '%s-%s' % (date.year, (date.month - 1) // 3 + 1)
    elif interval == 'year':
        return date.strftime('%Y')
    raise Exception('invalid interval')


###########################################################################
##              Process Handling and External Processes                  ##
###########################################################################

class _Reader(threading.Thread):
    """Class used for reading the streams in L{execute}"""

    def __init__(self, stream, name, listener=None):
        threading.Thread.__init__(self)
        self.stream = stream
        self.name = name
        self.out = ""
        self.listener = listener

    def run(self):
        """Read self.stream until it stops. If a listener is present,
        call it for every read line"""
        if self.listener:
            while True:
                s = self.stream.readline()
                self.listener(self.name, s)
                if not s:
                    self.listener(self.name, None)
                    break
                self.out += s
        else:
            self.out = self.stream.read()


def executepipe(cmd, listener=None, listenOut=False, outonly=False, **kargs):
    """Execute a command, yielding an input pipe for writing,
    then yielding out and err, using threads to avoid deadlock

    Useful for large sending input streams for processes with
    simple communication (everything in, then everything out)

    @param cmd: the process to run
    @param listener: An optional a listener, which should be a function that
      accepts two arguments (source, message). This function will be
      called for every line read from the error and output streams,
      where source is 'out' or 'err' depending on the source and
      message will be the line read. The listener will be called once
      per stream with a non-True message to indicate closure of that
      stream. These calls will come from the worker threads, so (especially
      if listenOut is True) this might cause multithreading issues.
    @param listenOut: if False (default), only the error stream will be used
      for the listener, otherwise both error and output stream will be used.
    @param outonly: if True, return only the out part, and raise an exception
      if there is any data on the error stream
    """
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, close_fds=True, **kargs)
    outr = _Reader(p.stdout, "out", listenOut and listener)
    errr = _Reader(p.stderr, "err", listener)
    outr.start()
    errr.start()
    #print "Yielding input pipe"
    yield p.stdin
    #print "Closing input pipe"
    p.stdin.close()

    #print "Joining outr"
    outr.join()
    #print "Joining errr"
    errr.join()
    #print "Returning..."
    if outonly:
        e = errr.out.strip()
        if e: raise Exception("Error on executing %r:\n%s" % (cmd, e))
        yield outr.out
    yield outr.out, errr.out


###########################################################################
##                          Type Checking                                ##
###########################################################################

def is_sequence(obj, exclude_strings=False):
    """Check whether obj is a sequence, possibly excluding strings"""
    if exclude_strings and isinstance(obj, basestring):
        return False
    return hasattr(obj, "__getslice__")

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

def htmlImageObject(bytes, format='png'):
    """Create embedded html image object"""
    #does not really belong here?
    data = base64.b64encode(bytes)
    return ("<object type='image/%s' data='data:image/%s;base64,%s'></object>"
            % (format, format, data))


