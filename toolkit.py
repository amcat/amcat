#!/bin/env python2.2

import types,re,mx.DateTime,sys,time,os,random,math,gzip,pickle,optparse
from threading import Thread

_USE_CURSES = 1

def valuesAroundIndex(seq, index):
    n = len(seq)
    rels = flatten([(0,)] + zip(range(1,n), range(-1, -n, -1)))
    abss = (index + rel for rel in rels if rel >= -index and rel < n - index)
    for i in abss:
        yield seq[i]

def product(seq):
    result = 1
    for x in seq:
        result *= x
    return result

def readids(file):
    if isString(file):
        file = open(file)
    return [int(line) for line in file if line.strip()]

class DefaultDict(dict):
    def __init__(self,default):
        self.default = default
    def __getitem__(self, key):
        if not key in self:
            default = self.default
            if isCallable(default): default=default()
            self[key]=default
            return default
        return self.get(key)

# determine which zip function to use: izip is better but only from python2.3
if int("%s%s%s" % sys.version_info[:3]) < 230:
    zipfunc = zip
else:
    import itertools
    zipfunc = itertools.izip

def tmp():
    if os.name == 'nt': return 'd:/tmp'
    else: return '/tmp'

def tempdir():
    fn = "%s/temp-%s"% (tmp(), int(random.random() * 1000000000))
    os.mkdir(fn)
    return fn

def mkdir(newdir):
        """
        Thanks to Trent Mick
        http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/82465
        works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
        """
        if os.path.isdir(newdir):
            pass
        elif os.path.isfile(newdir):
            raise OSError("a file with the same name as the desired " \
                          "dir, '%s', already exists." % newdir)
        else:
            head, tail = os.path.split(newdir)
            if head and not os.path.isdir(head):
                _mkdir(head)
            if tail:
                os.mkdir(newdir)

def tempfilename(suffix = None,prefix="temp-"):
    i = 0
    while i < 1000:
        i += 1
        fn = "%s/%s%s%s"% (tmp(), prefix, int(random.random() * 1000000000), suffix or "")
        if not os.path.exists(fn): return fn
    raise Exception("Could not create temp file!")

def tempfile(mode='w'):
    i = 0
    while i < 1000:
        i += 1
        fn = "%s/temp-%s"% (tmp(), int(random.random() * 1000000000))
        try:
            f = open(fn, mode)
            return open(fn, mode)
        except:
            pass
    raise Exception("Could not create temp file!")

def writefile(str, fn = None, tmpsuffix = None, tmpprefix="temp-", encoding="latin-1"):
    if not fn: fn = tempfilename(tmpsuffix, tmpprefix)
    fn = openfile(fn, 'w')
    fn.write(str.encode(encoding))
    fn.close()
    return fn.name

def indexed(seq):
    import sys
    return zip(seq, xrange(sys.maxint))

def reverse(seq):
    seq = list(seq)
    seq.reverse()
    return seq


def log2(x, pwr = 2):
        return math.log(x) / math.log(pwr)



############## COLOURS ################

_COLOURS={'red':31, 'green':32,'yellow':33, 'blue':34, 'purple':35,'cyan':36}
def coloured(colour, text, bold=2):
    c = _COLOURS.get(colour,0)
    return '\033[%s;%sm%s\033[m' % (c, bold, text)

############## DEBUGGING ################
def error(string):
    warn(string, 1, 'red')

def warn(string, newline = 1, colour = None):
    if colour and _USE_CURSES: string = coloured(colour, string, 1)

    
    if isString(string):
        if type(string) == unicode:
            sys.stderr.write(string.encode('latin-1', 'replace'))
        else:
            sys.stderr.write(string)
    else:
        sys.stderr.write(string.__str__())
    if newline: sys.stderr.write('\n')
    

global _DEBUG
_DEBUG = 0
_DEBUG_COLOURS = 'red', 'yellow', 'purple', 'green','blue','blue','blue'

class Debug:
    def __init__(this, modulename, debuglevel):
        this.module = modulename
        this.debuglevel = debuglevel
    def __call__(this, level, message, newline=1):
        if level <= this.debuglevel:
            col = _DEBUG_COLOURS[level-1]
            if newline <> 2: # print prefix
                warn("[%-10s %s] " % (this.module[:10], time.strftime("%Y-%m-%d %H:%M")), 0, col)
            warn(message, newline, col)
    def ok(this, level):
        this(level, " OK!", newline=2)
    def fail(this, level):
        this(level, " FAILED!", newline=2)
        

def debug(string, level=1, newline=1):
    global _DEBUG
    if _DEBUG >= level:
        warn("%s %s %s" % (time.strftime("%Y-%m-%d %H:%M"), level, string), newline)

def setDebug(level = 1):
    global _DEBUG
    _DEBUG = level

class Ticker:
    def __init__(this, interval = 10):
        this.interval = interval
        this.i = 0
        this.start = time.time()
        this.last = time.time()

    def warn(this, msg, reset=False, interval = None, estimate=None, newline=True, detail=0):
        if interval: this.interval = interval
        if estimate:
            this.reset()
            ovg = math.log10(estimate)
            if ovg%1 < 0.5: ovg -= 1
            if detail: ovg -= detail
            this.interval = 10**(int(ovg))
            
            msg += " (%s steps / %s)" % (estimate, this.interval)
            
        now = time.time()
        warn("%10f\t%10f\t%d\t%s" % (now-this.last, now-this.start, this.i, msg), newline=newline)
        this.last = now
        if reset: this.reset()

    def reset(this):
        this.i = 0
            
    def tick(this, msg = "", interval = None):
        if interval: this.interval = interval
        this.i += 1
        #if not msg: msg = "".join(map(lambda x:x%2 and " " or chr(32 + random.random() * 80), range(95)))
        if this.i % this.interval == 0:
            this.warn("%s\t%s" % (this.i, msg))

    def totaltime(this):
        warn("Total time: %10f" % (time.time() - this.start))

ticker = Ticker()


############## TESTING TYPES ##############
def isDict(obj):
    return type(obj) == types.DictType

def isSequence(obj, excludeStrings = False):
    if excludeStrings and isString(obj): return False
    return "__len__" in dir(obj)

def isIterable(obj, excludeStrings = False):
    if excludeStrings and isString(obj): return False
    return "__iter__" in dir(obj)

def isString(obj):
    return type(obj) in types.StringTypes

def isNumeric(obj):
    # misnomer!
    return type(obj) == types.IntType

def isFloat(obj):
    return type(obj) == types.FloatType

def isFile(obj):
    return type(obj) == types.FileType

def isCallable(obj):
    return type(obj) in (types.MethodType, types.FunctionType, types.ClassType, types.TypeType)

def isDate(obj):
    # kan beter!
    return type(obj) == mx.DateTime.DateTime

def istrue(x):
    return not not x


    
############## LISTS         ##############

def joinformat(elem, fmt, none):
    if elem is None: return ""#none
    if type(elem) == unicode:
        elem = elem.encode('latin-1', 'replace')
    return fmt%elem

def join(seq, sep="\t", fmt="%s", none=None):
    return sep.join([joinformat(x, fmt, none) for x in seq])

def get(seq, i, default = None):
    if len(seq) > i:
        return seq[i]
    else:
        return default

def outerjoin(seq1, seq2):
    res = []
    for a in seq1:
        res += [(a,b) for b in seq2]
    return res

def remove(wall, brick):
    return [x for x in wall if x not in brick]
    
def flatten(seq):

    if isString(seq) or not isSequence(seq):
      return [seq]
    result = []
    for x in seq:
      result += flatten(x)
    return result     

def shift(seq, default=None):
    if seq:
        return seq.pop(0)
    else:
        return default

def unique(seq):
    return dict(zip(seq,seq)).keys()

def sum(seq):
    import operator
    return reduce(operator.add, seq)
    
############## HASHMAPS      ##############

def dictFromStr(str):
    try:
        exec("dict="+str)
        return dict
    except:
        return None
        

def sortByValue(dict, reverse=0):
    list = dict.items()
    list.sort(lambda a,b:cmp(a[1],b[1]))
    if reverse: list.reverse()
    return list

def sortByKeys(dict, reverse=0):
    list = dict.items()
    list.sort(lambda a,b:cmp(a[0],b[0]))
    if reverse: list.reverse()
    return list

def sorted(seq):
    if isDict(seq):
        seq = seq.keys()
    seq.sort()
    return seq

############# REGULAR EXPRESSIONS ##########

global _MATCH
_MATCH = None

def rematch(pattern, string):
    """
    Can be used to test match in if expression and still use results
    """
    global _MATCH
    _MATCH = re.match(pattern, string)
    return _MATCH

def research(pattern, string):
    """
    Can be used to test match in if expression and still use results
    """
    global _MATCH
    _MATCH = re.search(pattern, string)
    return _MATCH

def count(pattern, text, useRE=1):
    if useRE:
      #Eigen even testen of het een r.e. is return len(re.split(pattern, text)) - 1
      return len(pattern.split(text)) - 1
    else:
      return len(text.split(pattern)) - 1
      
############# DATETIME ROUTINES #############

_MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
_MONTHS2 = ['jan','feb','mar','apr','mai','jun','jul','aug','sep','okt','nov','dez'];
_MONTHS3 = ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec']; #Added by jcjacobi for iex.nl
_MONTHS4 = ['jan','feb','maa','apr','mei','jun','jul','aug','sep','okt','nov','dec']; #Added by jcjacobi for texel-plaza
_MONTHS6 = ['jan','feb','mae','apr','mei','jun','jul','aug','sep','okt','nov','dec']; #Added by wva for sueddeutsche zeitung
_MONTHS5 = ['janv','fevr','mars','avri','mai','juin','juil','aout','sept','octo','nove','dece']; #Added by Lonneke voor fr

def average(seq):
    return float(sum(seq)) / len(seq)

def dayofweek(date):
    return date.Format('%D')

def dateStr():
    return mx.DateTime.now().Format('%Y-%m-%d %H:%M:%S')

BROUWERS_CMAP = {'e': u'\xeb\x84\x89\x82\x8a\x88', 'i': u'\x8b\x8c', 'u' : u'\x81', 'a' : u'\x85', 'o' : u'\x94\x93', 'c' : u'\x87', 'n':u'\xa4'}

def stripAccents(s, map = None):
    #s = str(s)
    if type(s) <> unicode:
        s = unicode(s, "latin-1")
    if not map: map = {'a': u'\xe1\xe0\xe2\xe4', 'i': u'\xed\xec\xee\xef', 'u':u'\xfa\xf9\xfb\xfc',
                       'e':u'\xe9\xe8\xea\xeb','o':u'\xf3\xf2\xf4\xf6','c':u'\xe7', 'C' : u'\xc7'}
    for key, val in map.items():
        for trg in val:
            try:
                s = s.replace(trg, key)
            except Exception, e:
                print `s`, `trg`, `key`
                raise e
    return s

def monthnr(str):
    strShort = str.lower().strip()[:3]
    strLonger = str.lower().strip()[:4]
    if strShort in _MONTHS: return _MONTHS.index(strShort) + 1
    if strShort in _MONTHS2: return _MONTHS2.index(strShort) + 1
    if strShort in _MONTHS3: return _MONTHS3.index(strShort) + 1
    if strShort in _MONTHS4: return _MONTHS4.index(strShort) + 1
    if strShort in _MONTHS6: return _MONTHS6.index(strShort) + 1
    if strLonger in _MONTHS5: return _MONTHS5.index(strLonger) + 1
    return None
    

def readDate(str, lax=False, rejectPre1970=False):
    if str == None: return None
    
    orig = str

    str = stripAccents(str)

    time = None
    if ':' in str:
        m = re.match("(.*?)(\d+:[\d:]+)",str)
        if m:
            str, time = m.groups()

    m = None

    if research("(\d{4})[-/](\d{1,2})[-/](\d{1,2})",str):
        ymd = [_MATCH.group(1),_MATCH.group(2),_MATCH.group(3)]
        m = 1
    elif research("(\d{1,2})[-/](\d{1,2})[-/](\d{4})",str):
        ymd = [_MATCH.group(3),_MATCH.group(2),_MATCH.group(1)]
        m = 2
    elif research("(\w+),?\s+(\d{1,2})\s*,?\s+(\d{4})",str) and monthnr(_MATCH.group(1)):
        ymd = [_MATCH.group(3), monthnr(_MATCH.group(1)), _MATCH.group(2)]
        m = 3
    elif research("(\w+)\s+(\d{1,2})\s*,?\s+(\d{4})",str) and monthnr(_MATCH.group(1)):
        ymd = [_MATCH.group(3), monthnr(_MATCH.group(1)), _MATCH.group(2)]
        m = 4
    elif research("(\d{1,2})(?:\w\w?|\.)?\s+(\w*)\s+(\d{4})",str) and monthnr(_MATCH.group(2)):
        ymd = [_MATCH.group(3), monthnr(_MATCH.group(2)), _MATCH.group(1)]
        m = 5
    elif research("\w*?,?\s*(\d{1,2})\s+(\w+)\s+(\d{4})",str) and monthnr(_MATCH.group(2)):
        ymd = [_MATCH.group(3), monthnr(_MATCH.group(2)), _MATCH.group(1)]
        m = 6
    elif research("(\d{1,2})\.?\s+(\w*)\s+(\d{4})",str) and monthnr(_MATCH.group(2)):
        ymd = [_MATCH.group(3), monthnr(_MATCH.group(2)), _MATCH.group(1)]
        m = 7
    elif research("(\d{2}) (\w+) (\d{4})",str) and monthnr(_MATCH.group(2)):
        ymd = [_MATCH.group(3), monthnr(_MATCH.group(2)), _MATCH.group(1)]
        m = 8  
    else:
        m = 99
        if lax: return None
        if research("(\d{1,2})\.?\s+(\w*)\s+(\d{4})",str): print _MATCH.group(2).lower()[:3]
        raise ValueError("Cannot parsexxxx datetime string %s" % str)

    if time:
        if research("(\d\d?):(\d\d?):(\d\d?)", time):
            hms = [_MATCH.group(1), _MATCH.group(2),_MATCH.group(3)]
            m = m + .1
        elif research("(\d\d?):(\d\d?)", time):
            hms = [_MATCH.group(1), _MATCH.group(2), 0]
            m = m + .1
        else:
            m = m + .99
            if not lax:
                raise ValueError("Could not parse time part ('%s') of datetime string '%s'" % (time, orig))

    try:
        if time: ymd += hms
        ymd = map(int, ymd)

        if ymd[0]<1970 and rejectPre1970:
            print ("Rejecting datetime string %s -> %s -> %s"% (str, m, ymd))
            if lax: return None
            raise ValueError("Rejecting datetime string %s -> %s -> %s"% (str, m, ymd))

        if ymd[0] < 1900: print "date: %s %s -> %s" % (str, m, ymd)

        return mx.DateTime.DateTime(*ymd)
    except Exception,e :
        warn("Exception on reading datetime %s [m=%s,ymd='%s']:\n%s" % (orig, m,`ymd`, e))
        if lax: return None
        else: raise


def writeDate(datetime, lenient=0):
    if lenient and (datetime is None): return None
    return datetime.Format("%Y-%m-%d")

def writeMonth(month, lenient=0):
    if lenient and (month is None): return None
    if type(month) is mx.DateTime.DateTimeType:
        return month.Format("%B")
    return mx.DateTime.DateTime(1,int(month)).Format("%B")

def writeDateTime(datetime, lenient=0, year=True, seconds=True):
    if lenient and (datetime is None): return None
    if lenient and type(datetime) in types.StringTypes: return datetime 
    format = year and "%Y-%m-%d" or "%m-%d"
    format += seconds and " %H:%M:%S" or " %H:%M"
    return datetime.Format(format)

############### FILE I/O            #################

def openfile(file, mode = None, skipheader=0):
    """
    if <file> is a string, opens and returns the file with that name; otherwise, returns <file>
    """
    if isString(file):
        if file[-3:] == '.gz':
            if mode:
                return gzip.open(file,mode)
            else:
                return gzip.open(file)
        if mode:
            return open(file, mode)
        else:
            return open(file)
    if skipheader: file.readline()
    return file

def filesInDir(path):
    return map(lambda x: path + os.sep + x ,os.listdir(path))

def readCSVTable(file, sep="\t"):
    # interpret header
    n = 0
    titles = file.readline()[:-1].split(sep)
    for n in range(len(titles)):
        if not titles[n]:
            titles[n] = "var%s"%n
            
    # read data        
    for line in file:
        vals = line.strip().split(sep)
        vals += [None] * (len(titles) - len(vals))
        yield dict(zip(titles, vals))




############### STRING MANIPULATION #################

_POSTRANS = {'Adj':'J','Art':'R', 'Num':'M', 'Pron': 'O', 'Punc' : 'U'}
def wplToWc(s, lax=False):
    """
    Transforms a word/pos/lemma string to a lemma/category string. Categories are:
    A (Adjective or Adverb), N (Noun), X (Auxilliary verbs), V (other verbs),
    R (aRticles), M (Numbers), P (Prep), O (Pronoun), C (Conj), I (Int), U (Punct),
    E (Proper Noun ('E'igennaam)
    If parsing fails, returns None if lax is True, otherwise raises an exception


    """
    import cnlp
    result = cnlp.wplToWc(s)
    if not result:
        if lax: return None
        else: raise Exception("Could not convert %r" % s)
    return result
#     try:
#         w,p,l = s.split("/")
#         if p.startswith('V(hulp'): p = 'X'
#         if p.startswith('N(eigen'): p = 'E'
#         else: p = _POSTRANS.get(p.split('(')[0], p[0])
#         return l+'/'+p
#     except Exception, e: 
#         if lax: return None
#         else: raise



def pad(string, desiredLength = None, desiredMod = 8, padchr = ' '):
    if desiredLength:
        inc = len(string) - desiredLength
    else:
        inc = desiredMod - (len(string) % desiredMod)
    return string + padchr * inc
    
def read(string, sep = None, maxsplit = 0):
    string = string.strip()
    if sep <> None:
        return map(read, string.split(sep, maxsplit))
    else:
        return num(string, 1)

def asInt(string):
    if string is None: return None
    if type(string) == int:
        return string
    if re.match("[0-9]+", string.strip()):
        return int(string)
    return None

def num(string, lenient=0):
    try:
        if rematch("^-?[0-9]*,[0-9]*$", string.strip()):
            string = string.replace(',', '.')
        if not '.' in string:
            return int(string)
        elif rematch("^([0-9]+)\.0*$", string.strip()):
            #print string.strip()
            return float(_MATCH.group(1))
        else:
            return float(string)
    except:
        if lenient:
            return string
        else:
            raise

class Output:
    def __init__(self, delimiter='\t', format='%s', floatformat='%1.3f', pre='', post=''):
        self.delimiter = delimiter
        self.format = format
        self.floatformat = floatformat
        self.pre = pre
        self.post = post
    def fmt(self, x):
        if isFloat(x): return self.floatformat
        else: return self.format
    def output(self, *seq):
        if len(seq)==1 and isSequence(seq[0]): seq = seq[0]
        values = [self.pre + (self.fmt(value) % (value,)) + self.post for value in seq]
        return self.delimiter.join(values)
        

def output(*seq, **kargs):
    return Output(**kargs).output(*seq)
                  
def chomp(obj):
    """
    if obj is a string, removes trailing newline
    if obj is a sequence, chomps all members
    """
    if isString(obj):
        if obj[-1] == '\n':
            return obj[:-1]
        else:
            return obj
    else:
        return map(chomp, obj)

def strip(obj):
    """
    if obj is a string, strip it
    if obj is a sequence, strip all members
    """
    if isString(obj):
        return obj.strip()
    else:
        return map(strip, obj)
        

def quotesql(strOrSeq):
    """
    if str is seq: return tuple of quotesql(values)
    if str is string: escapes any quotes and backslashes in the string and returns the string in quotes
    otherwise: returns `str`
    """
    if strOrSeq is None:
        return 'null'
    elif isString(strOrSeq):
        #strOrSeq = re.sub(r"\\", r"\\\\", strOrSeq)
        strOrSeq = re.sub("'", "''", strOrSeq)
        return "'%s'" % strOrSeq
    elif isSequence(strOrSeq):
        return tuple(map(quotesql, strOrSeq))
    elif type(strOrSeq) == bool:
        return strOrSeq and "1" or "0"
    else:
        return "%s"%strOrSeq

def quotesql_psql(strOrSeq):
    """
    if str is seq: return tuple of quotesql(values)
    if str is string: escapes any quotes and backslashes in the string and returns the string in quotes
    otherwise: returns `str`
    """
    if strOrSeq is None:
        return 'null'
    elif isString(strOrSeq):
        strOrSeq = re.sub(r"\\", r"\\\\", strOrSeq)
        strOrSeq = re.sub("'", "\\'", strOrSeq)
        return "'%s'" % strOrSeq
    elif isSequence(strOrSeq):
        return tuple(map(quotesql, strOrSeq))
    else:
        return "%s"%strOrSeq

def clean(str, level=0, lower=0,droptags=0, escapehtml=0, keeptabs=0):
    """
    Cleans a string by reducing all whitespace to single spaces and stripping
    any leading or trailing whitespace
    """
    if not str: return str
    if droptags: str=re.sub("<[^>]{,20}>","",str)
    if keeptabs:
        str = re.sub("[ \\n]+", " ", str)
    else:
        str = re.sub("\s+" ," ", str)
    if level==3: str = re.sub(r"\W","",str)
    if level==2: str = re.sub(r"[^\w,\. ]","",str)
    elif level==1:
        if keeptabs:
            str = re.sub(r"[^?%\w,\.\t ;'<>=()\":/\&-]","",str)
        else:
            str = re.sub(r"[^?%\w,\. ;'<>=()\":/\&-]","",str)
    if lower: str=str.lower()
    if escapehtml:
        str = str.replace("&","&amp;")
        str = str.replace('"', "&quot;")
    return str.strip()
    

def pairs(seq, lax=0):
    """
    Transforms [s1,s2,s3,s4,...] into [(s1,s2),(s3,s4),...]
    If lax, a trailing single value will be paired with None
    otherwise, an exception is thrown if there is an off number of items
    """

    if len(seq) % 2:
        if lax:
            return pairs(seq[:-1]) + [(seq[-1],None)]
        else:
            raise Exception("Non-lax pairing needs even number of items in sequence")

    return map(lambda y:(seq[y],seq[y+1]),range(0,len(seq),2))



def xmlElementText(docOrNode=None, tagname = None):
    if tagname is not None:
        node = docOrNode.getElementsByTagName(tagname)
        if node: node = node[0]
    else:
        node = docOrNode
    if not node: return None
    return "".join("%s"%child.nodeValue for child in node.childNodes)


def getcached(filename, defaultfunction):
    try:
        filename = '%s/%s' % (tmp() ,filename)
        warn("Attempting to load pickled results from %s"%filename, newline = 0)
        f = open(filename, 'rb')
        data = pickle.load(f)
        warn(" OK!")
        return data
    except Exception, e:
        warn("Failed\n%s\nExecuting %s..." % (e,defaultfunction))
        data = defaultfunction()
        warn("Caching result...")
        pickle.dump(data, open(filename, 'wb'))
        return data

def best(list, function, returnScore=False, inverse=False):
    score = None
    result = None
    inverse = inverse and -1 or 1
    for elem in list:
        s = function(elem) * inverse
        if (score == None or s > score):
            score = s
            result = elem
    if returnScore:
        return result, score * inverse
    else:
        return result

class Argument(object):
    def __init__(self, name, help = None, optional = False):
        self.name = name
        self.help = help
        self.optional = optional

class OptionParser(optparse.OptionParser):
    
    def __init__(self, *args, **kargs):
        optparse.OptionParser.__init__(self, *args, **kargs)
        if not 'usage' in kargs:
            self.usage = True # provide own default in get_usage
        self.arguments = []

    def get_usage(self):
        if self.usage == True:
            nclose = 0
            usage = "%prog [options]"
            for x in self.arguments:
                usage += " "
                if x.optional:
                    usage += "["
                    nclose += 1
                usage += x.name
            usage += "]"*nclose
            return self.formatter.format_usage(
                self.expand_prog_name(usage))
        else:
            return optparse.OptionParser.get_usage(self)

    def add_argument(self, argument, *args, **kargs):
        if not isinstance(argument, Argument):
            argument = Argument(argument, *args, **kargs)
        if len(self.arguments) > 1 and self.arguments[-1].optional and not argument.optional:
            raise TypeError("Optional argument cannot be followed by obligatory arguments")
        self.arguments.append(argument)

    def parse_args(self, *args, **kargs):
        opts, args = optparse.OptionParser.parse_args(self, *args, **kargs)
        n = len(args)
        if n > len(self.arguments):
            self.error("Too many arguments!")
        if n < len(self.arguments) and not self.arguments[n].optional:
            if n == 0:
                self.print_help(sys.stderr)
                sys.exit(2)
            self.error("Argument '%s' not optional!" % self.arguments[n].name)
        args += [None] * (len(self.arguments) - n)
        return opts, args
                      
    def format_help(self,  *args, **kargs):
        help = optparse.OptionParser.format_help(self,  *args, **kargs)
        if self.arguments:
            # should use formatter
            help += "\nArguments:\n"
            for argument in self.arguments:
                help += "  %-21s %s\n" % (argument.name, argument.help or "")
        return help
            
            
def jpegsize(fn):
    import struct
    # Dummy read to skip header ID
    stream = open(fn)
    stream.read(2)
    while True:
        # Extract the segment header.
        (marker, code, length) = struct.unpack("!BBH", stream.read(4))

        # Verify that it's a valid segment.
        if marker != 0xFF:
            return None, None
        elif code >= 0xC0 and code <= 0xC3:
            # Segments that contain size info
            (y, x) = struct.unpack("!xHH", stream.read(5))
            error = "no error"
            break
        else:
            # Dummy read to skip over data
            stream.read(length - 2)
            
    return x, y
    
    
class Popen3:
   """
   This is a deadlock-safe version of popen that returns
   an object with errorlevel, out (a string) and err (a string).
   (capturestderr may not work under windows.)
   Example: print Popen3('grep spam','\n\nhere spam\n\n').out
   """
   def __init__(self,command,input=None,capturestderr=None):
       import tempfile
       outfile=tempfile.mktemp()
       command="( %s ) > %s" % (command,outfile)
       if input:
           infile=tempfile.mktemp()
           open(infile,"w").write(input)
           command=command+" <"+infile
       if capturestderr:
           errfile=tempfile.mktemp()
           command=command+" 2>"+errfile
       self.errorlevel=os.system(command) >> 8
       self.out=open(outfile,"r").read()
       os.remove(outfile)
       if input:
           os.remove(infile)
       if capturestderr:
           self.err=open(errfile,"r").read()
           os.remove(errfile)
    


class Reader(Thread):
    def __init__(self, stream, name, listener = None):
        Thread.__init__(self)
        self.stream = stream
        self.name = name
        self.out = ""
        self.listener = listener
    def run(self):
        if self.listener:
            while True:
                s = self.stream.readline()
                self.listener(self.name, s)
                if not s: break
                self.out += s
        else:
            self.out = self.stream.read()

def warnlistener(stream, message):
    if message:
        warn(message)
        
def execute(cmd, input=None, listener=None, listenOut=False):
    """
    Executes a process using popen3 using multiple threads
    to avoid deadlocks. Returns a pair (out, err).
    
    You may provide a listener, which should be a function that
    accepts two arguments (source, message). This function will be
    called for every line read from the error and output streams,
    where source is 'out' or 'err' depending on the source and
    message will be the line read. if listenOut if False (default),
    only the error stream will be read, otherwise both error and
    output stream will be read. The listener will be called once per
    stream with a non-True message to indicate closure of that stream.
    These calls will come from the worker threads, so (especially if
    listenOut is True) this might cause multithreading issues.
    """
    stdin, stdout, stderr = os.popen3(cmd)
    outr = Reader(stdout, "out", listenOut and listener)
    errr = Reader(stderr, "err", listener)
    outr.start()
    errr.start()
    #print "writing input"
    if input:
        stdin.write(input)
    stdin.close()
    #print "waiting for threads to exit"
    outr.join()
    errr.join()
    return outr.out, errr.out


def splitlist(list, chunksize):
    for i in range(0, len(list), chunksize):
        yield list[i:i+chunksize]

def choose(seq, scorer, returnscore=False):
    best = None
    bestscore = None
    for e in seq:
        score = scorer(e)
        if bestscore is None or score > bestscore:
            best = e
            bestscore = score
    if returnscore:
        return best, bestscore
    return best

if __name__ == "__main__":
    import sys
    print choose(["123","45","999"], lambda x: int(x)*-1, True)
    
