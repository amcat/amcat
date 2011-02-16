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
   (deprecated functions may import AmCAT modules internally)
 - Each public function should be documented!
 - It should pass pychecker (+pylint?) without warnings
 - We should try to make good test cases in test/test_toolkit.py

This toolkit is divided into a number of sections, please stick to
this organisation!
 - decorators
 - sequence functions
 - mapping functions
 - string/unicode functions
 - date(time) functions
 - statistical functions
 - file handling
 - process handling and external processes
 - type checking
 - misc functions
 - deprecated functions and imports
"""

from __future__ import unicode_literals, print_function, absolute_import
import warnings, os, random, gzip, types, datetime, itertools, re, collections
import threading, subprocess, sys, colorsys, base64, time, inspect, logging
import htmlentitydefs, string
try: import mx.DateTime
except: pass

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

def cached(func):
    """
    Decorate a method without arguments to cache results

    Uses self.__id__ as cache key. If not given, uses self
    """
    vals = {}
    def inner(self):
        """Check whether the 'self' is known, is so return cached value"""
        try: iden = self.__id__()
        except AttributeError: iden = self
        if iden not in vals:
            vals[iden] = func(self)
        return vals[iden]
    inner._vals = vals
    return inner

def printargs(func):
    """This decorator dumps out the arguments passed to a function before calling it

    Source: U{http://wiki.python.org/moin/PythonDecoratorLibrary}
    """
    argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
    fname = func.func_name
    def echo_func(*args,**kwargs):
        print("%s(%s)" % (fname, ', '.join(
                    '%s=%r' % entry
                    for entry in zip(argnames,args) + kwargs.items())))
        return func(*args, **kwargs)
    return echo_func

###########################################################################
##                      Statistical Functions                            ##
###########################################################################

def average(seq):
    """Compute the mean of sequence seq"""
    # note: use iteration over sum(x) / len(x) to avoid iterating twice
    # and for compatability with generators
    s, n = 0., 0
    for e in seq:
        if e is not None:
            s += e; n += 1
    return s / n if n > 0 else None

def stdev(seq):
    """Compute the stdev of seq"""
    seq = list(seq)
    avg = average(seq)
    s, n = 0.0, 0
    for e in seq:
        if e is not None:
            s += (e - avg)**2
            n += 1
    var = s / n-1 if n-1 > 0 else None
    if var: return var ** .5

def correlate(aa, bs):
    """Compute the correlation between sequences aa and bs"""
    ma = average(aa)
    mb = average(bs)
    teller = sum([(a-ma) * (b-mb) for (a, b) in zip(aa, bs)])
    noemer = (len(aa) - 1 ) * stdev(aa) * stdev(bs)
    if not noemer : return None
    return teller / noemer

###########################################################################
##                          File Handling                                ##
###########################################################################

def openfile(filename, mode = None, skipheader=False):
    """
    Open the given filename, handling zipped files

    @type filename: str or file. In the latter case, return the file unmodified
    @param filename: The file name. If it ends with .gz, uses gzip.open rather than open
    @param mode: an optional mode to pass to open
    @param skipheader: if True, skip one line from the file
    @return a file object corresponding to file
    """
    if isString(filename):
        opener = gzip.open if filename.endswith('.gz') else open
        if mode:
            f = opener(filename, mode)
        else:
            f = opener(filename)
    else:
        f = filename
    if skipheader: f.readline()
    return f


def mkdir(newdir):
    """
    Create the directory C{newdir}; and parents as needed

    From: U{http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/82465}

    @type newdir: string
    @param newdir: Name of the directory to create.
      If a regular file exists with this name, raises an exception
      If the directory exists, returns silently
    @return: None
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                          "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            mkdir(head)
        if tail:
            os.mkdir(newdir)


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

def writefile(string, fn = None, tmpsuffix = None, tmpprefix="temp-",
              encoding="latin-1"):
    """
    Create a new file, write the given string to it, and close it

    @type string: unicode (or ascii-encoded bytes)
    @param string: The content for the new file
    @param fn: The file name. If None, create a temp file using L{tempfilename}
    @param tmpsuffix: optional suffic to pass to L{tempfilename}
    @param tmpprefix: optional suffic to pass to L{tempfilename}
    @param encoding: the encoding to use for the contents
    @return: the file name of the file (useful if fn was None)
    """
    if not fn: fn = tempfilename(tmpsuffix, tmpprefix)
    fn = openfile(fn, 'w')
    fn.write(string.encode(encoding))
    fn.close()
    return fn.name


###########################################################################
##                     Sequence functions                                ##
###########################################################################

def flatten(seq):
    """Flattens one level of a sequence of sequences"""
    return itertools.chain(*seq)
    

def ints2ranges(seq, presorted=False):
    """Converts a seuence of integers into from, to pairs

    Given a list of comparable items, create a sequence of (from, to) pairs
    that would yield a sequence set-equivalent to the original.

    i.e.
    >>> set(flatten(range(fro, to+1) for (fro, to) in ints2ranges(seq))) == set(seq)
    
    for all sequences of integers

    @param seq: any iterable of ints
    @param presorted: if True, do not sort seq
    @return: a generator of (from, to) pairs of integers
    """
    if not presorted: seq = sorted(seq)
    start, prev, = None, None
    for i in sorted(seq):
        if start is None: start = i
        elif i > prev + 1:
            yield start, prev
            start = i
        prev = i
    if prev is not None:
        yield start, prev


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

def pairs(seq, lax=False):
    """Transforms [s1,s2,s3,s4,...] into [(s1,s2),(s3,s4),...]

    @param seq: the indexable sequence (list or tuple) to transform
    @param lax: If True a trailing single value will be paired with None
        otherwise, an exception is thrown if there is an odd number of items
    """
    if len(seq) % 2:
        if lax:
            return pairs(seq[:-1]) + [(seq[-1], None)]
        else:
            raise ValueError("Non-lax pairing needs even number of items in sequence")
    return zip(seq[::2], seq[1::2])



def getseq(sequence, seqtypes=(list, tuple, set), pref=list, stringok=False, convertscalar=False):
    """Ensures that the sequences is list/tuple/set and changes if necessary
    
    Makes sure that the sequence is a 'proper' sequence (and not
    an iterator/generator). If it is, return the sequence, otherwise
    create a list out of it and return that.

    @param sequence: the sequence to check
    @param seqtypes: allowable sequence types
    @param pref: the sequence type to change into if necessary
    @param stringok: treat string/unicode as sequence?
    @param convertscalar: convert scalar to [scalar]?
    @return: the original sequence if allowed, otherwise pref(sequence)
    """
    if isIterable(sequence, excludeStrings=not stringok):
        return sequence if isinstance(sequence, seqtypes) else pref(sequence)
    elif convertscalar:
        return pref([sequence])
    else:
        raise TypeError("Cannot create a sequence out of %r" % sequence)


def count(seq):
    """Return the number of elements in seq, also works for generators"""
    i = 0
    for dummy in seq: i += 1
    return i
def head(seq, filterfunc=None):
    """Return the first element in seq (for which filterfunc(.) is True)"""
    for val in seq:
        if (filterfunc is None) or filterfunc(val):
            return val

def choose(seq, scorer, returnscore=False, verbose=False):
    """Choose the best element in seq according to scorer

    @param seq: the sequence to choose from
    @param scorer: a function that returns a score for each element
    @param returnscore: if True, will return a (element, score) tuple
    @param verbose: if True, print output while choosing (for debugging)
    @return: the best element (unless returnscore)
    """
    best = None
    bestscore = None
    for e in seq:
        score = scorer(e)
        better = (bestscore is None) or (score > bestscore)
        if verbose: print("%s %r, score=%s, best so far=%s" %
                          (better and "accepting" or "rejecting", e, score, bestscore))
        if better:
            best = e
            bestscore = score
    if returnscore:
        return best, bestscore
    return best


def chomped(seq=sys.stdin, skipblanks=True, transform=None):
    """Return non-blank chomped lines from seq"""
    for e in seq:
        e = e.rstrip('\n')
        if skipblanks and not e: continue
        if transform:
            e = transform(e)
            if skipblanks and not e: continue
        yield e
        
def totuple(v):
    """Function to convert `value` to a tuple.
        
    @type idcolumn: tuple, list, str, int, unicode, or None
    @param idcolumn: value to convert to a tuple"""
    if v is None: return ()
    elif type(v) in (str, unicode, int): return (v,)
    
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

def intlist(seq=sys.stdin):
    """Return integers from seq, skipping blank lines"""
    for el in seq:
        if el.strip(): yield int(el)

def naturalSortKey(key):
    """Return a  sort key for an element that sorts numbers sensibly"""
    if type(key) != unicode: key = str(key)
    convert = lambda text: int(text) if text.isdigit() else text 
    return map(convert, re.split('([0-9]+)', key))

@deprecated
def naturalSort(sequence):
    """B{Deprecated: use sorted(key=naturalSortKey)}"""
    return sorted(sequence, key=naturalSortKey) 


                
def splitlist(sequence, itemsperbatch=100, buffercall=None, yieldelements=False):
    """Split a list into smaller lists

    @param sequence: the iterable to split
    @param itemsperbatch: the size of the desired splits
    @param buffercall: if given, buffercall is called once per subsequence
      (e.g. to allow caching)
    @param yieldelements: if True, yield individual elements rather than subsequences
    @return: yields subsequences of the same type as sequence, unless that was a generator,
      in which case lists are yielded. If yieldelements is True, always yield individual
      elements
    """
    def _splitlist(sequence, itemsperbatch):
        """Split a sequence or iterable into sublists"""
        if isSequence(sequence): # use slicing
            for i in xrange(0, len(sequence), itemsperbatch):
                yield sequence[i:i+itemsperbatch]
        else: # use iterating, copying into a buffer
            # can be more efficient by reusing buffer object...
            bufferlist = []
            for s in sequence:
                bufferlist.append(s)
                if len(bufferlist) >= itemsperbatch:
                    yield bufferlist
                    bufferlist = []
            if bufferlist: yield bufferlist
    
    for subsequence in _splitlist(sequence, itemsperbatch):
        if buffercall: buffercall(subsequence)
        if yieldelements:
            for e in subsequence: yield e
        else:
            yield subsequence

def pad(sequence, minlength, padwith=None, chopexcess=True):
    sequence = getseq(sequence, seqtypes=(list,))
    if len(sequence) > minlength and chopexcess:
        return sequence[:minlength]
    elif len(sequence) >= minlength: return sequence
    else: return sequence + [padwith] * (minlength - len(sequence))

        
            
@deprecated
def buffer(sequence, buffercall, buffersize=100):
    """B{Deprecated: please use splitlist(..., yieldelements=True)}"""
    return splitlist(sequence, buffersize, buffercall, yieldelements=True)


def unique(iterable, key=None):
    "List unique elements, preserving order. Remember all elements ever seen."
    # from http://docs.python.org/library/itertools.html#recipes
    # unique('AAAABBBCCDAABBB') --> A B C D
    # unique('ABBCcAD', str.lower) --> A B C D
    seen = set()
    seen_add = seen.add # for performance?
    if key is None:
        for element in itertools.ifilterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element

def zipp(*iterables):
    """Zip function with added functionality
    At the moment, raises Exception if iterable are not of same size"""
    #TODO: more elegant if we use iterators rather than coerce to sequence
    if not iterables: return ()
    seqs = map(getseq, iterables)
    l0 = len(seqs[0])
    if not all(l0 == len(it) for it in seqs[1:]):
        raise ValueError("Unequal iterable length")
    return zip(*seqs)
            
                
###########################################################################
##                      Mapping functions                                ##
###########################################################################

class multidict(collections.defaultdict):
    """A dictionary of key : set pairs"""
    def __init__(self, seq):
        """Create a new multidict from a seq of key,value pairs (with duplicate keys)"""
        collections.defaultdict.__init__(self, set)
        if seq:
            for kv in seq:
                if kv:
                    self.add(*kv)
    def add(self, key, value):
        self[key].add(value)

def sortByValue(dictionary, reverse=False):
    """Sort a dictionary by values, optionally in descending order"""
    if isinstance(dictionary, dict):
        items = dictionary.iteritems()
    else:
        items = dictionary
    l = sorted(items, key= lambda kv : kv[1])
    if reverse: l = list(reversed(l))
    return l


class Indexer(object):
    """Assign objects an index number"""
    def __init__(self):
        self.objects = [] # nr -> obj
        self.index = {} # obj -> nr
    def getNumber(self, obj):
        """Get or create the index number of obj"""
        return head(self.getNumbers(obj))
    def getNumbers(self, *objs):
        """Yield (possibly new) index numbers for mulitple objects"""
        for obj in objs:
            nr = self.index.get(obj)
            if nr is None:
                nr = len(self.objects)
                self.objects.append(obj)
                self.index[obj] = nr
            yield nr

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

def countmany(objects):
    """Convenience method to create a counter, count, and return it"""
    c = Counter()
    c.countmany(objects)
    return c

@deprecated
def DefaultDict(*args, **kargs):
    """B{Deprecated: please use collections.defaultdict}"""
    return collections.defaultdict(*args, **kargs)

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

def stripAccents(s, usemap = ACCENTS_MAP):
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
    if droptags: string = re.sub("<[^>]{,30}>", "", string)
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


def warn(string):
    fn, lineno, func = getCaller()
    module = getCallingModule()

    log = logging.getLogger()
    rec = log.makeRecord(module, logging.WARN, fn, lineno,
                         string, [], exc_info=None, func=func)
    log.handle(rec)
    
def toJSON(value):
    """Convert `value` to a string json can encode. Generators are converted
    to lists, NoneTypes to empty strings.
    
    @type value: anything
    @param value: value you wish to convert to a json-friendly type"""    
    if type(value) in (types.GeneratorType, types.TupleType, types.ListType):
        return map(toJSON, value)
    elif type(value) in (types.BooleanType, types.IntType):
        return value
    elif type(value) is datetime.datetime:
        return value.ctime()
    
    if value: return unicode(value)
    
    return ''

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
              ('feb', 'fevr', 'feve'),
              ('mar', 'mrt', 'maa', 'mar', 'mai'),
              ('apr', 'avri', 'abri'),
              ('may', 'mai', 'mei', 'mayo', 'maggio'),
              ('jun', 'juin','giugno'),
              ('jul', 'juil', 'luglio'),
              ('aug', 'aout', 'agos'),
              ('sep', 'setem', 'settembre'),
              ('oct', 'okt', 'out', 'ottobre'),
              ('nov'),
              ('dec', 'dez', 'dici', 'dicembre'))
"""Tuple of 12 tuples containing month name (prefixes)""" 

class _DateFormat(object):
    """Format definition for parsing dates"""
    def __init__(self, expr, yeargroup=3, monthgroup=2, daygroup=1,
                 monthisname=False, swapamerican=False):
        self.expr = expr
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
    _DateFormat("(\d{4})[-/](\d{1,2})[-/](\d{1,2})", 1,2,3),
    _DateFormat("(\d{1,2})[-/](\d{1,2})[-/](\d{4})", 3,2,1,swapamerican=True),
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

        
def readDate(string, lax=False, rejectPre1970=False, american=False):
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
        datestr = stripAccents(string)

        time = None
        if ':' in datestr:
            m = re.match("(.*?)(\d+:[\d:]+)", datestr)
            if m:
                datestr, timestr = m.groups()
                try: time = tuple(map(int, timestr.split(":")))
                except ValueError: time = []
                if len(time) == 3: pass
                elif len(time) == 2: time = time + (0,)
                elif lax: time = None
                else: raise ValueError("Could not parse time part "
                                       +"('%s') of datetime string '%s'"
                                       % (timestr, string))
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
                        date = int(s[2]), i+1, int(s[0])
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

def getYW(date):
    """Return a float containing year.weeknumber (eg 2002.52)"""
    try:
        y, w, dummy = date.isocalendar() # datetime
    except AttributeError:
        y, w, dummy = date.iso_week # mx
    return y + w/100.0

def getYM(date):
    """Return a float containing year.monthnumber (eg 2002.12)"""
    return date.year + date.month / 100.0

def getYQ(date):
    """Return a float containing year.quarter (eg 2002.4)"""
    return date.year + (int((date.month-1)/3)+1)/10.0

def toDate(date):
    """Convert a string, datetime.datetime, or mx.DateTime into a datetime"""
    if type(date) == str:
        return readDate(date)
    return datetime.datetime(*date.timetuple()[:6])

def cmpDate(date1, date2):
    """Compares to date-like arguments (see L{toDate}), returning cmp-score"""
    date1, date2 = map(toDate, (date1, date2))
    return cmp(date1, date2)


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

class ErrorReader(threading.Thread):
    def __init__(self, stream):
        threading.Thread.__init__(self)
        self.stream = stream

        import fcntl
        fd = self.stream.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        
    def run(self):
        while True:
            try:
                err = self.stream.read()
            except IOError, e:
                if e.errno not in (11,):
                    raise
                print(e.errno)
            else:
                if err.strip():
                    raise Exception("Unexpected message:\n%s" % err)
            time.sleep(0.1)
            
def executepipe(cmd, listener=None, listenOut=False, outonly=False):
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
                         stderr=subprocess.PIPE, close_fds=True)
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


def execute(cmd, inputbytes=None, **kargs):
    """Execute a process, feed it inputbytes, and return (output, error)

    Convenience method to call executepipe and write input to the
    process' stdin.

    @param cmd: the process to run
    @param inputbytes: (optional) input to send to the process' input pipe
    @param kargs: optional listener and listenout to send to executepipe
    """
    #print "Starting execute %r" % cmd
    gen = executepipe(cmd, **kargs)
    #print "Getting input stream"
    pipe = gen.next()
    if inputbytes:
        #print "Writing %i bytes" % len(inputbytes)
        pipe.write(inputbytes)
    return gen.next()
    
def ps2pdf(ps):
    """Call ps2pdf on the given ps bytes, returning pdf bytes"""
    out, err = execute("ps2pdf - -", ps)
    if err: raise Exception(err)
    return out

def convertImage(image, informat, outformat=None, quality=None, scale=None, trim=False):
    """Call imagemagick 'convert' on the given image bytes, returning image bytes

    @param image: the image bytes
    @param informat: the input format (e.g. 'png')
    @param outformat: the output format, if different from input
    @type quality: float (0..1)
    @param quality: if given, reduce quality to given percentage
    @type scale: float (0..1)
    @param scale: if given, reduce size to given percentage
    """
    cmd = 'convert '
    if scale: cmd += ' -geometry %1.2f%%x%1.2f%% ' % (scale*100, scale*100)
    if quality: cmd += ' -quality %i ' % int(quality*100)
    if trim: cmd += ' -trim '
    
    cmd += ' %s:- %s:-' % (informat, outformat or informat)
    out, err = execute(cmd, image)
    if err and err.strip():
        warn(err)
    return out

###########################################################################
##                          Type Checking                                ##
###########################################################################

def isString(obj):
    """Check whether obj is a string (str/unicode)"""
    return type(obj) in types.StringTypes

def isDate(obj):
    """Check whether obj is a mx.DateTime or datetime"""
    if 'mx' in globals() and isinstance(obj, mx.DateTime.DateTimeType):
        return True
    return isinstance(obj, datetime.datetime)

def isSequence(obj, excludeStrings = False):
    """Check whether obj is a sequence, possibly excluding strings"""
    if excludeStrings and isString(obj): return False
    if hasattr(obj, "__getslice__"): return True
    else: return False

def isIterable(obj, excludeStrings = False):
    """Check whether obj is iterable, possibly excluding strings"""
    if excludeStrings and isString(obj): return False
    try: iter(obj); return True
    except TypeError: return False


    
###########################################################################
##                         Misc. functions                               ##
###########################################################################
# Please try to keep this one clean...

def getCaller(depth=1):
    """Return the filename, lineno, function of the caller

    A depth of 1 signifies the caller of the function calling this function.
    Depth 2 would be its caller etc.
    """
    depth = depth + 1 # me, caller, caller's caller
    return inspect.stack()[depth][1:4]
    
def getCallingModule(depth=1):
    """Return the module name of the caller (see L{getCaller})"""
    depth = depth + 1 # me, caller, caller's caller
    caller = inspect.stack()[depth]
    return caller[0].f_globals['__name__']


def getCallingModuleFilename(depth=1):
    """Return the module name of the caller (see L{getCaller})"""
    depth = depth + 1 # me, caller, caller's caller
    caller = inspect.stack()[depth]
    return caller[1]

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


def getREGroups(regExp, text, flags=re.DOTALL, groups=(1,), match=True):
    """Return the selected groups from the regexp, or None(s) if no match

    Convenience function for::
    
      >>>m = re.match(regExp, text)
      ...if m:
      ...  a = m.group(1)
      ...  #do something

    @param regExp: the expression to test
    """
    match = re.search(regExp, text, flags)
    if match:
        return match.group(*groups)
    if len(groups) == 1:
        return None
    return (None,) * len(groups) 


def isnull(x, alt):
    """Return alf if x is None else x"""
    return alt if x is None else x

def hasattrv2(obj, attrs):
    """Accepts dot-seperated attributes. This allow for non-shallow checking
    
    @obj: an object
    @attrs: dot-seperated attribute
    
    @example:
    >>> class A(object): pass
    ...
    >>> class B(object): pass
    ...
    >>> B.foo = 'bar'
    >>> A.B = B
    >>> hasattrv2(A, 'B.foo')
    True
    >>> hasattrv2(A, 'B.bar')
    False
    """
    try: getattrv2(obj, attrs)
    except AttributeError:
        return False
    return True

def getattrv2(obj, attrs):
    """Accepts dot-seperated attributes. This allows for non-shallow getting
    
    (See: hasattrv2)"""
    for attr in attrs.split('.'):
        obj = getattr(obj, attr)
    return obj

###########################################################################
##                 Deprecated functions and imports                      ##
###########################################################################

@deprecated
def isDict(obj):
    """B{Deprecated: use L{isinstance}} Check whether obj is a dict"""
    return isinstance(obj, dict)

@deprecated
def isFloat(obj):
    """B{Deprecated: use L{isinstance}} Check whether obj is a float"""
    return type(obj) == types.FloatType


@deprecated
def indexed(seq):
    """B{Deprecated: use L{enumerate}} Enumerate with index following value"""
    return [(e, i) for (i, e) in enumerate(seq)]

@deprecated
def reverse(seq):
    """B{Deprecated: use L{reversed}} Reverse seq"""
    return reversed(seq)


@deprecated
def log2(x, pwr = 2):
    """B{Deprecated: use C{math.log}} Return the 2-log of x"""
    import math
    return math.log(x, base=pwr)

#### old ticker connection ####


@deprecated
def tickerate(*args, **kargs):
    """B{Deprecated: please use L{ticker.tickerate}}"""
    import ticker as _ticker
    return _ticker.tickerate(*args, **kargs)

class _ticker_proxy(object):
    """B{Deprecated: please use L{ticker.ticker()}"""
    def __getattr__(self, name):
        if "__" not in name:
            warnings.warn(DeprecationWarning("Deprecated: please use ticker.ticker().%s" % (name)))
        import ticker as _ticker
        return getattr(_ticker.ticker(), name)
ticker = _ticker_proxy()
    
class Debug:
    """B{Deprecated: please use amcatlogging}"""
    @deprecated
    def __init__(self, modulename=None, debuglevel=None, printer=warn):
        """B{Deprecated: please use amcatlogging}"""
        pass
    @deprecated
    def __call__(self, message, *dummy, **dummy2):
        """B{Deprecated: please use amcatlogging}"""
        warn(message)
    @deprecated
    def ok(self, level):
        """B{Deprecated: please use amcatlogging}"""
        self(level, " OK!")
    @deprecated
    def fail(self, level):
        """B{Deprecated: please use amcatlogging}"""
        self(level, " FAILED!")
    
    
@deprecated
def dictFromStr(string, unicode=False):
    """B{deprecated: what is this for?} Create a dictionary from a string"""
    try:
        dictionary = eval(string)
    except:
        return None
    if unicode and dictionary:
        for k, dummy in dictionary.items():
            if type(dictionary[k]) == string:
                dictionary[k] = dictionary[k].decode('utf-8')
    return dictionary

@deprecated
def sortByKeys(dictionary, reverse=False):
    """B{deprecated: duplicates built-in C{sorted}} Sort a dictionary by keys"""
    l = sorted(dictionary.iteritems())
    if reverse: l = list(reversed(l))
    return l

@deprecated
def debug(string, *dummy, **dummy2):
    """B{Deprecated: please use amcatlogging}"""
    Debug()(string)

@deprecated
def setDebug(*dummy, **dummy2):
    """B{Deprecated: please use amcatlogging}"""
    pass

@deprecated
def quotesql(strOrSeq):
    """B{Deprecated: please use L{dbtoolkit.quotesql}}"""
    import dbtoolkit
    return dbtoolkit.quotesql(strOrSeq)


@deprecated
def returnTraceback():
    """B{Deprecated: please use traceback.format_exc()}"""
    import traceback
    return traceback.format_exc()

@deprecated
def getGroup1(*args, **kargs):
    """B{Deprecated: please use getREGroups}"""
    return getREGroups(*args, **kargs)

@deprecated
def intSelection(db, *args, **kargs):
    """B{Deprecated: please use amcatDB.intSelectionSQL}"""
    return db.intSelectionSQL(*args, **kargs)

if __name__ == '__main__':
    import amcatlogging ;amcatlogging.setStreamHandler()
    warn("zoiets?")

