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
 - Should not depend on any module outside to 2.5+ standard library
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
 - file handling
 - process handling and external processes
 - type checking
 - misc functions
 - deprecated functions and imports
"""

from __future__ import unicode_literals, print_function, absolute_import
import warnings
import os
import random
import types
import datetime
import itertools
import re
import collections
import threading
import subprocess
import sys
import colorsys
import base64
import logging
import htmlentitydefs
import string

try: import mx.DateTime
except: pass

log = logging.getLogger(__name__)

###########################################################################
##                               Decorators                              ##
###########################################################################

def _deprecationwarning(msg):
    warnings.warn(DeprecationWarning(msg))

def deprecated(func, msg = 'Call to deprecated function %(funcname)s.'):
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
                        + (func.__doc__ or "").replace("@","\@").replace("L{","l{"))
    new_func.__dict__.update(func.__dict__)
    return new_func

def dictionary(func):
    """This decorator converts a generator yielding (key, value) to a dictionary."""
    def _dictionary(*args, **kwargs):
        return dict(tuple(func(*args, **kwargs)))
    return _dictionary

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
##                          File Handling                                ##
###########################################################################

def tmp():
    """
    Return the proper temp dir for this os.

    Note: The windows behaviour is usually incorrect
    @return: string containing the temp dir name
    """
    if os.name == u'nt': return u'd:/tmp'
    else: return u'/tmp'

def tempfilename(suffix=None, prefix="temp-", tempdir=None):
    """Generate a non-existing filename in the temporary files folder

    @param suffix: an optional suffix (e.g. '.txt')
    @param prefix: the prefix for the file
    @param tempdir: the dir to place the file in, defaults to -L{tmp}()
    @return: a filename of the form tempdir/prefix-000000suffix
    """
    if tempdir is None: tempdir = tmp()
    for dummy in range(1000):
        r = random.randint(0, 1000000000)
        fn = "%s/%s%s%s"% (tempdir, prefix, r, suffix or "")
        if not os.path.exists(fn): return fn
    raise Exception("Could not create temp file!")

###########################################################################
##                     Sequence functions                                ##
###########################################################################

def flatten(seq):
    """Flattens one level of a sequence of sequences"""
    return itertools.chain(*seq)



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


def head(seq, filterfunc=None):
    """Return the first element in seq (for which filterfunc(.) is True)"""
    for val in seq:
        if (filterfunc is None) or filterfunc(val):
            return val


def totuple(v):
    """Function to convert `value` to a tuple.

    @type idcolumn: tuple, list, str, int, unicode, or None
    @param idcolumn: value to convert to a tuple"""
    if v is None: return ()
    elif type(v) in (str, unicode, int, long): return (v,)

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


def splitlist(sequence, itemsperbatch=100):
    """Split a list into smaller lists

    @param sequence: the iterable to split
    @param itemsperbatch: the size of the desired splits
    @return: yields subsequences of the same type as sequence, unless that was a generator,
      in which case lists are yielded.
    """
    if hasattr(sequence, '__getslice__'): # use slicing
        for i in xrange(0, len(sequence), itemsperbatch):
            yield sequence[i:i+itemsperbatch]
    else: # use iterating, copying into a buffer
        bufferlist = []
        for s in sequence:
            bufferlist.append(s)
            if len(bufferlist) >= itemsperbatch:
                yield bufferlist
                bufferlist = []
        if bufferlist: yield bufferlist



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

def sortByValue(dictionary, reverse=False):
    """Sort a dictionary by values, optionally in descending order"""
    if isinstance(dictionary, dict):
        items = dictionary.iteritems()
    else:
        items = dictionary
    l = sorted(items, key= lambda kv : kv[1])
    if reverse: l = list(reversed(l))
    return l


def prnt(string, *args, **kargs):
    """Print the string, optionally applying %args or %kargs

    Two keyword-only arguments are popped from kargs
      - stream: (keyword-only; popped from kargs; default sys.stdout)
        the stream to write to
      - end: (keyword-only; popped from kargs; default newline)
        an optional final string to write to the stream

    """
    stream = kargs.pop("stream", sys.stdout)
    end = kargs.pop("end", '\n')
    if args:
        string = string % args
    elif kargs:
        string = string % kargs
    stream.write(string)
    if end: stream.write(end)



class Counter(collections.defaultdict):
    """Subclass of defaultdict(int) that simplifies counting stuff"""
    def __init__(self, keys=None):
        collections.defaultdict.__init__(self, int)
        if keys:
            for k in keys:
                self[k] = 0
    def count(self, obj, count=1):
        """Count the given object"""
        self[obj] += count
    def countmany(self, objects):
        """Count the given objects, may be a {object : n} mapping"""
        if 'keys' in dir(objects):
            for o, c in objects.items():
                self.count(o, count=c)
        else:
            for o in objects:
                self.count(o)
    def items(self, reverse=True):
        """Return the items from most to least frequent"""
        return sortByValue(super(Counter, self).iteritems(), reverse=reverse)
    def prnt(self, threshold=None, outfunc=prnt, reverse=True):
        """Print the items with optional threshold"""
        for k, v in self.items(reverse=reverse):
            if (not threshold) or  v >= threshold:
                outfunc("%4i\t%s" % (v, k))


###########################################################################
##                   String/Unicode functions                            ##
###########################################################################

ACCENTS_MAP =  {u'a': u'\xe0\xe1\xe2\xe3\xe4\xe5',
                u'c': u'\xe7',
                u'e': u'\xe9\xe8\xea\xeb',
                u'i': u'\xec\xed\xee\xef',
                u'n': u'\xf1',
                u'o': u'\xf3\xf2\xf4\xf6',
                u'u': u'\xf9\xfa\xfb\xfc',
                u'y': u'\xfd\xff',

                u'A' : u'\xc0\xc1\xc2\xc3\xc4\xc5',
                u'C' : u'\xc7',
                u'E' : u'\xc8\xc9\xca\xcb',
                u'I' : u'\xcc\xcd\xce\xcf',
                u'N' : u'\xd1',
                u'O' : u'\xd2\xd3\xd4\xd5\xd6',
                u'U' : u'\xd9\xda\xdb\xdc',
                u'Y' : u'\xdd\xdf',
                u's' : u'\u0161\u015f',
                u'ss' : u'\xdf',
                u'?' : u'\xbf',
                u"'" : u'\x91\x92\x82\u2018\u2019\u201a\u201b\xab\xbb\xb0',
                u'"' : u'\x93\x94\x84\u201c\u201d\u201e\u201f\xa8',
                u'-' : u'\x96\x97\u2010\u2011\u2012\u2013\u2014\u2015',
                u'|' : u'\xa6',
                u'...' : u'\x85\u2026\u2025',
                u'.' : u'\u2024',
                u' ' : u'\x0c\xa0',
                u'\n' : u'\r',
                u"2" : u'\xb2',
                u"3" : u'\xb3',
                #u"(c)" : u'\xa9',
                }
"""Map of unaccented : accented pairs.

The values (accented) are strings where each character is an accented
version of the corresponding key (unaccented). The key can be of length>1
if appropriate (e.g. german sz, ellipsis)"""

def stripAccents(s, usemap = ACCENTS_MAP, latin1=False):
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

def unescapeHtml(text):
    """Removes HTML or XML character references and entities from a text string.

    @param text The HTML (or XML) source text.
    @return The plain text, as a Unicode string, if necessary.
    """
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

def clean(string, level=0, lower=False, droptags=False, escapehtml=False, keeptabs=False,
          normalizeWhitespace=True):
    """Clean a string with various options

    @param string: the string to clean
    @param level: if 3, keep only word characters (r.e. \W)
      if 25 (2.5), keep spaces and word-characters
      if 2, keep spaces, comma, period, and word-characters
      if 1: keep most puntuations and possibly tabs
      if 0: only process other options
    @param lower: whether to call .lower() on the string
    @param droptags: whether to remove all xml-tags
    @param escapehtml: whether to call unescapehtml
    @param keeptabs: whether to keep tabs (if level 1 or normazeWhitespace)
    @param normalizeWhitespace: replace all adjacent whitespace with a single
      space (excepting tabs if keeptabs is True)
    @return: the cleaned string
    """
    if not string: return string
    if droptags: string = re.sub(r"<[^>]{0,30}>", "", string)
    if normalizeWhitespace:
        string = re.sub("[ \\n]+" if keeptabs else "\s+", " ", string)
    if level == 3: string = re.sub(r"\W", "", string)
    if level == 25: string = re.sub(r"[^\w ]", "", string)
    if level == 2: string = re.sub(r"[^\w,\. ]", "", string)
    elif level == 1:
        if keeptabs:
            string = re.sub(r"[^?%\w,\.\t ;'<>=()\":/\&-]", "", string)
        else:
            string = re.sub(r"[^?%\w,\. ;'<>=()\":/\&-]", "", string)
    if lower: string = string.lower()
    if escapehtml:
        string = unescapeHtml(string)
    return string.strip()

def random_alphanum(size=10):
    return ''.join([random.choice(string.letters + string.digits) for i in range(size)])


def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    elif not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        s = unicode(s)
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s



###########################################################################
##                     Date(time) functions                              ##
###########################################################################

MONTHNAMES = (('jan', 'janv', 'ener', 'gennaio'),
              ('feb', 'fevr', 'feve', 'f\xe9vrier'),
              ('mar', 'mrt', 'maa', 'mar', 'm\xe4rz', 'maerz'),
              ('apr', 'avri', 'abri'),
              ('may', 'mai', 'mei', 'mayo', 'maggio', 'm\xe4rz'),
              ('jun', 'juin','giugno'),
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
        if y < 40: y = 2000 + y
        elif y < 100: y = 1900 + y
        # dmy vs mdy
        if american and self.swapamerican:
            m, d = d, m
        return y, m, d

_DATEFORMATS = (
    _DateFormat("(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})", 1,2,3),
    _DateFormat("(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})", 3,2,1,swapamerican=True),
    _DateFormat("(\w+),?\s+(\d{1,2})\s*,?\s+(\d{4})",3,1,2,True),
    _DateFormat("(\w+)\s+(\d{1,2})\s*,?\s+(\d{4})",  3,1,2,True),
    _DateFormat("(\d{1,2})(?:\w\w?|\.)?\s+(\w*)\s+(\d{4})",3,2,1,True),
    _DateFormat("\w*?,?\s*(\d{1,2})\s+(\w+)\s+(\d{4})",3,2,1,True),
    _DateFormat("(\d{1,2})\.?\s+(\w*)\s+(\d{4})",    3,2,1,True),
    _DateFormat("(\d{1,2})[- ](\w+)[- ](\d{2,4})",   3,2,1,True),
    _DateFormat("(\w+) (\d{1,2}), (\d{4})",          3,1,2,True),
    _DateFormat("(\d{1,2})[-/](\d{1,2})[-/](\d{2})", 3,2,1,swapamerican=True),

)

def _monthnr(monthname):
    """Try to get a month number corresponding to the month
    name (prefix) in monthname"""
    for i, names in enumerate(MONTHNAMES):
        for name in names:
            if monthname.lower().startswith(name.lower()):
                return i+1


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
    if string == None: return None
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
                try: time = tuple(map(int, timestr.split(":")))
                except ValueError: time = []
                if len(time) == 3: pass
                elif len(time) == 2: time = time + (0,)
                elif lax: time = None
                else: raise ValueError("Could not parse time part "
                                       +"('%s') of datetime string '%s'"
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
                    date = int(year), i+1, int(day)

        if not date:
            # For '22 November 2006 Wednesday 10:23 AM (Central European Time)'
            s = datestr.split(' ')
            if len(s)>2:
                for i, prefixes in enumerate(MONTHNAMES):
                    if s[1].startswith(prefixes):
                        try:
                            date = int(s[2]), i+1, int(s[0])
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
    except Exception,e:
        import traceback
        trace = traceback.format_exc()
        #warn("Exception on reading datetime %s:\n%s\n%s" % (string, e, trace))
        if lax: return None
        else: raise
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
        return '%s-%s' % (date.year, (date.month-1)//3 + 1)
    elif interval == 'year':
        return date.strftime('%Y')
    raise Exception('invalid interval')


###########################################################################
##              Process Handling and External Processes                  ##
###########################################################################




class _Reader(threading.Thread):
    """Class used for reading the streams in L{execute}"""
    def __init__(self, stream, name, listener = None):
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

def isSequence(obj, excludeStrings = False):
    """Check whether obj is a sequence, possibly excluding strings"""
    if excludeStrings and isinstance(obj, basestring): return False
    if hasattr(obj, "__getslice__"): return True
    else: return False

def isIterable(obj, excludeStrings = False):
    """Check whether obj is iterable, possibly excluding strings"""
    if excludeStrings and isinstance(obj, basestring): return False
    try: iter(obj); return True
    except TypeError: return False



###########################################################################
##                         Misc. functions                               ##
###########################################################################
# Please try to keep this one clean...



def HSVtoHTML(h, s, v):
    """Convert HSV (HSB) colour to HTML hex string"""
    rgb = colorsys.hsv_to_rgb(h, s, v)
    if not rgb: raise TypeError("Cannot convert hsv (%s,%s,%s)!" % (h,s,v))
    return RGBtoHTML(*rgb)

def RGBtoHTML(r, g, b):
    """Convert RGB colour to HTML hex string"""
    hexcolor = '#%02x%02x%02x' % (r*255, g*255, b*255)
    return hexcolor


def htmlImageObject(bytes, format='png'):
    """Create embedded html image object"""
    #does not really belong here?
    data = base64.b64encode(bytes)
    return ("<object type='image/%s' data='data:image/%s;base64,%s'></object>"
            % (format, format, data))



def isnull(x, alt):
    """Return alf if x is None else x"""
    return alt if x is None else x

