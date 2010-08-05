#!/bin/env python2.2

import types,re,sys,time,os,random,math,gzip,pickle,optparse, threading, csv, htmlentitydefs, odict, collections, operator, functools, subprocess, colorsys, base64
from idlabel import Identity, IDLabel
try:
    import mx.DateTime
except: print "Ik kon mx>DateTime niet importeren"
from datetime import datetime

_USE_CURSES = 1

def valuesAroundIndex(seq, index):
    n = len(seq)
    rels = flatten([(0,)] + zip(range(1,n), range(-1, -n, -1)))
    abss = (index + rel for rel in rels if rel >= -index and rel < n - index)
    for i in abss:
        yield seq[i]

def product(seq):
    return reduce(operator.mul, seq)

def readids(file):
    if isString(file):
        file = open(file)
    return [int(line) for line in file if line.strip()]

DefaultDict = collections.defaultdict

class DefaultOrderedDict(odict.OrderedDict):
    def __init__(self,default):
        odict.OrderedDict.__init__(self)
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

def tempfilename(suffix = None,prefix="temp-",tempdir=None):
    if tempdir is None: tempdir = tmp()
    for i in range(1000):
        fn = "%s/%s%s%s"% (tempdir, prefix, int(random.random() * 1000000000), suffix or "")
        if not os.path.exists(fn): return fn
    raise Exception("Could not create temp file!")

def tempfile(mode='w'):
    for i in range(1000):
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
            sys.stderr.write(string.encode('utf-8'))
        else:
            sys.stderr.write(string)
    else:
        sys.stderr.write(str(string))
    if newline: sys.stderr.write('\n')
    

global _DEBUG
_DEBUG = 0
_DEBUG_THREADNAME = False
_DEBUG_COLOURS = 'red', 'yellow', 'purple', 'green','blue','blue','blue'

_HTML_COLOURS = {'yellow' : '#daa520'}

def HTMLDebug(writer, message, newline=1, colour=None):
    style = " style='color:%s'" % _HTML_COLOURS.get(colour, colour) if colour else ""
    if newline <> 2: writer.write("<div class='debug' %s>" % style)
    writer.write(str(message))
    if newline: writer.write("</div>")
    writer.req.flush()

def HTMLDebugger(writer):
    return functools.partial(HTMLDebug, writer)

class Debug:
    def __init__(this, modulename, debuglevel, printer=warn):
        this.module = modulename
        this.debuglevel = debuglevel
        this.printer = printer
        this.last = time.time()
    def __call__(this, level, message, newline=1):
        if not this.printer: return
        if level <= this.debuglevel:
            col = _DEBUG_COLOURS[level-1]
            if newline <> 2: # print prefix
                this.printer("[%-10s %s %s %03.4f] " % (this.module[:10], threading.currentThread().getName(), time.strftime("%Y-%m-%dT%H:%M:%S"), time.time() - this.last), 0, col)
            this.printer(message, newline and 2, col)
            this.last = time.time()
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

def tickerate(seq, msg=None, getlen=True, useticker=None, detail=0):
    if msg is None: msg = "Starting iteration"
    if useticker is None: useticker = ticker
    if getlen:
        if type(seq) not in (list, tuple, set):
            seq = list(seq)
        ticker.warn(msg, estimate=len(seq), detail=detail)
    else:
        ticker.warn(msg)
    for x in seq:
        ticker.tick()
        yield x
    
class Ticker:
    def __init__(this, interval = 10, markThread=True, stream=sys.stderr):
        this.interval = interval
        this.i = 0
        this.start = time.time()
        this.last = time.time()
        this.markThread = markThread
        this.stream = stream

    def warn(this, msg, reset=False, interval = None, estimate=None, newline=True, detail=0):
        if interval: this.interval = interval
        if estimate:
            this.reset()
            ovg = math.log10(estimate)
            if ovg%1 < 0.5: ovg -= 1
            if detail: ovg -= detail
            this.interval = 10**(int(ovg))
            
            msg += " (%s steps / %s)" % (estimate, this.interval)

        if this.markThread and threading.currentThread().getName() <> 'MainThread':
            msg = "[%s] %s" % ( threading.currentThread().getName(), msg)
            
        now = time.time()
        this.stream.write("%10f\t%10f\t%d\t%s" % (now-this.last, now-this.start, this.i, msg))
        if newline: this.stream.write("\n")
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
    return isinstance(obj, dict)

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
    # wva: kan beter!
    # andreas: zoiets?
    if 'mx'  in globals():
        return isinstance(obj, mx.DateTime.DateTimeType) or isinstance(obj, datetime)
    else:
        return isinstance(obj, datetime)


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

def addToSeq(seq, element_or_seq, copy=False):
    # Why o why does python not have a uniform collection interface?
    # Must there be something that is better in java than in python?
    e = element_or_seq
    if type(seq) == list:
        if copy: seq = list(seq)
        if type(e) == list:
            seq += e
        elif isSequence(e):
            seq += list(e)
        else:
            seq.append(e)
    elif type(seq) == set:
        if copy: seq = set(seq)
        if type(e) == set:
            seq |= e
        elif isSequence(e):
            seq |= set(e)
        else:
            seq.add(e)
    else:
        raise Exception("Cannot add to type %s" % type(seq))
    return seq
    

def flatten(seq, toSet=False):
    if isString(seq) or not isSequence(seq):
      return [seq]
    result = set() if toSet else []
    for x in seq:
        if toSet:
            result |= flatten(x, toSet=True)
        else:
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

def dictFromStr(str, unicode=False):
    try:
        dict = eval(str)
    except:
        return None
    if unicode and dict:
        for k,v in dict.items():
            if type(dict[k]) == str:
                dict[k] = dict[k].decode('utf-8')
    return dict
        

def sortItems(list, reverse=False, byValue = False):
    i = byValue and 1 or 0
    list.sort(lambda a,b:cmp(a[i],b[i]))
    if reverse: list.reverse()
    return list
    
def sortByValue(dict, reverse=0):
    return sortItems(dict.items(), reverse, byValue=True)

def sortByKeys(dict, reverse=0):
    return sortItems(dict.items(), reverse, byValue=False)


#def sorted(seq):
#    if isDict(seq):
#        seq = seq.keys()
#    seq.sort()
#    return seq

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

def getYW(date):
    y,w,d = date.iso_week
    return y + w/100.0

def getYM(date):
    return date.year + date.month / 100.0

def getYQ(date):
    return date.year + (int((date.month-1)/3)+1)/10.0

def safediv(a, b):
    if not b: return None
    return float(a)/b

def average(seq):
    s, n = 0., 0
    for e in seq:
        if e is not None:
            s += e; n += 1
    return safediv(s, n)

def stdev(seq):
    seq = list(seq)
    avg = average(seq)
    s, n = 0.0, 0
    for e in seq:
        if e is not None:
            s += (e - avg)**2
    var = safediv(s, n-1)
    if var: return var ** .5

def correlate(aa,bs):
    ma = average(aa)
    mb = average(bs)
    teller =sum([(a-ma) * (b-mb) for (a,b) in zip(aa, bs)])
    noemer = (len(aa) - 1 ) * stdev(aa) * stdev(bs)
    if not noemer : return None
    return teller / noemer

def dayofweek(date):
    return date.Format('%D')

def dateStr():
    return mx.DateTime.now().Format('%Y-%m-%d %H:%M:%S')

BROUWERS_CMAP = {'e': u'\xeb\x84\x89\x82\x8a\x88', 'i': u'\x8b\x8c', 'u' : u'\x81', 'a' : u'\x85', 'o' : u'\x94\x93', 'c' : u'\x87', 'n':u'\xa4'}

def stripAccents(s, map = None):
    #s = str(s)
    if not s: return s
    if type(s) <> unicode:
        s = unicode(s, "latin-1")
    if not map: map = {u'a': u'\xe0\xe1\xe2\xe3\xe4\xe5',
                       u'c': u'\xe7',
                       u'e':u'\xe9\xe8\xea\xeb',
                       u'i': u'\xec\xed\xee\xef',
                       u'n': u'\xf1',
                       u'o' : u'\xf3\xf2\xf4\xf6',
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
                       u's' : u'\u0161',
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
    for key, val in map.items():
        for trg in val:
            try:
                s = s.replace(trg, key)
            except Exception, e:
                print `s`, `trg`, `key`
                raise e
    return s


ENTITY_MAP = {
    '&quot;' : "'",
    '&lt;' : "<",
    '&gt;' : ">",
    '&amp;' : "&",
    }

def unescapeHtml(text):
    """ From http://effbot.org/zone/re-sub.htm#unescape-html """
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
    text = re.sub("&#?\w+;", fixup, text)
    for k, v in ENTITY_MAP.items():
        text = text.replace(k,v)
    return text



_MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
_MONTHS2 = ['jan','feb','mar','apr','mai','jun','jul','aug','sep','okt','nov','dez'];
_MONTHS3 = ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec']; #Added by jcjacobi for iex.nl
_MONTHS4 = ['jan','feb','maa','apr','mei','jun','jul','aug','sep','okt','nov','dec']; #Added by jcjacobi for texel-plaza
_MONTHS5 = ['jan','feb','mae','apr','mei','jun','jul','aug','sep','okt','nov','dec']; #Added by wva for sueddeutsche zeitung
_MONTHS6 = ['janv','fevr','mars','avri','mai','juin','juil','aout','sept','octo','nove','dece']; #Added by Lonneke voor fr
_MONTHS7 = ['ener', 'febr', 'marz', 'abri', 'mayo', 'juni', 'juli', 'agos', 'sept', 'octu', 'novi','dici']


def germanmonth(s):
    print ">", s
    strShort = s.lower().strip()[:3]
    if strShort in _MONTHS6:
        return _MONTHS5.index(strShort) + 1
    return None

def monthnr(str):
    strShort = str.lower().strip()[:3]
    strLonger = str.lower().strip()[:4]
    if strShort in _MONTHS: return _MONTHS.index(strShort) + 1
    if strShort in _MONTHS2: return _MONTHS2.index(strShort) + 1
    if strShort in _MONTHS3: return _MONTHS3.index(strShort) + 1
    if strShort in _MONTHS4: return _MONTHS4.index(strShort) + 1
    if strShort in _MONTHS5: return _MONTHS5.index(strShort) + 1
    if strLonger in _MONTHS6: return _MONTHS6.index(strLonger) + 1
    if strLonger in _MONTHS7: return _MONTHS7.index(strLonger) + 1
    return None


def readDate(str, lax=False, rejectPre1970=False, american=False):
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
        if american: ymd[2], ymd[1] = ymd[1], ymd[2]
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
    elif research("(\d{1,2})[- ](\w+)[- ](\d{2,4})",str) and monthnr(_MATCH.group(2)):
        ymd = [_MATCH.group(3), monthnr(_MATCH.group(2)), _MATCH.group(1)]
        m = 8
    elif research("(\w+) (\d{1,2}), (\d{4})",str) and monthnr(_MATCH.group(1)):
        ymd = [_MATCH.group(3), monthnr(_MATCH.group(1)), _MATCH.group(2)]
        m = 9
    elif research("(\d{1,2})[-/](\d{1,2})[-/](\d{2})",str):
        ymd = [_MATCH.group(3),_MATCH.group(2),_MATCH.group(1)]
        if int(ymd[0]) < 40: ymd[0] = "20" + ymd[0]
        else: ymd[0] = "19" + ymd[0]
        if american: ymd[2], ymd[1] = ymd[1], ymd[2]
        m = 10
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

        if ymd[0] < 1900:
            if ymd[0] < 40: ymd[0] += 2000
            else: ymd[0] += 1900
            print "date: %s %s -> %s" % (str, m, ymd)


        if ymd[0]<1970 and rejectPre1970:
            print ("Rejecting datetime string %s -> %s -> %s"% (str, m, ymd))
            if lax: return None
            raise ValueError("Rejecting datetime string %s -> %s -> %s"% (str, m, ymd))

        return mx.DateTime.DateTime(*ymd)
    except Exception,e :
        warn("Exception on reading datetime %s [m=%s,ymd='%s']:\n%s" % (orig, m,`ymd`, e))
        if lax: return None
        else: raise


def writeDate(datetime, lenient=0):
    if lenient and (datetime is None): return None
    return datetime.strftime("%Y-%m-%d")

def writeMonth(month, lenient=0):
    if lenient and (month is None): return None
    if type(month) is mx.DateTime.DateTimeType:
        return month.Format("%B")
    return mx.DateTime.DateTime(1,int(month)).Format("%B")

def writeDateTime(datetimeObj, lenient=0, year=True, seconds=True):
    if lenient and (datetimeObj is None): return None
    if lenient and type(datetimeObj) in types.StringTypes: return datetimeObj
    format = year and "%Y-%m-%d" or "%m-%d"
    format += seconds and " %H:%M:%S" or " %H:%M"
    return datetimeObj.strftime(format)
    #if you want to make this function incompatible with datetime from the
    #standard library, use this (no sarcasm intended, datetime might cause
    #difficult to find bugs I'm not aware of):
    #return datetimeObj.Format(format)

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

def readCSVTable(file, strip=False, **kargs):

    if "sep" in kargs:
        kargs["delimiter"] = sep
        del(kargs["sep"])

    reader = csv.reader(file, **kargs)

    titles = None
    for line in reader:
        if not titles:
            # interpret header
            titles = line
            for i, title in enumerate(titles):
                if not title:
                    titles[i] = "var%i" % i
        else:
            # read data        
            vals = line
            if strip:
                
                vals = [x and x.strip() for x in vals]
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
    import dbtoolkit
    return dbtoolkit.quotesql(strOrSeq)

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
    if droptags: str=re.sub("<[^>]{,30}>","",str)
    if keeptabs:
        str = re.sub("[ \\n]+", " ", str)
    else:
        str = re.sub("\s+" ," ", str)
    if level==3: str = re.sub(r"\W","",str)
    if level==25: str = re.sub(r"[^\w ]","",str)
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
    


class Reader(threading.Thread):
    def __init__(self, stream, name, listener = None):
        threading.Thread.__init__(self)
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
    #stdin, stdout, stderr = os.popen3(cmd)
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    outr = Reader(p.stdout, "out", listenOut and listener)
    errr = Reader(p.stderr, "err", listener)
    outr.start()
    errr.start()
    #print "writing input"
    try:
        if input:
            p.stdin.write(input)
    finally:
        p.stdin.close()
    #print "waiting for threads to exit"
    outr.join()
    errr.join()
    return outr.out, errr.out

def executepipe(cmd, input=None, listener=None, listenOut=False):
    """
    Variant of execute that yields the input pipe for writing,
    and then yields the out and err.
    Useful for large sending input streams for processes with
    simple communication (everything in, then everything out)
    """
    #stdin, stdout, stderr = os.popen3(cmd)
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    outr = Reader(p.stdout, "out", listenOut and listener)
    errr = Reader(p.stderr, "err", listener)
    outr.start()
    errr.start()
    #print "writing input"
    yield p.stdin
    p.stdin.close()
    outr.join()
    errr.join()
    yield outr.out, errr.out


def ps2pdf(ps):
    out, err = execute("ps2pdf - -", ps)
    if err: raise Exception(err)
    return out

def splitlist(list, chunksize):
    for i in range(0, len(list), chunksize):
        yield list[i:i+chunksize]

def choose(seq, scorer, returnscore=False, verbose=False):
    best = None
    bestscore = None
    for e in seq:
        score = scorer(e)
        better = bestscore is None or score > bestscore
        if verbose: print "%s %r, score=%s, best so far=%s" % (better and "accepting" or "rejecting", e, score, bestscore)
        if better:
            best = e
            bestscore = score
    if returnscore:
        return best, bestscore
    return best

def test():
    return "test! dev2"

def intlist(seq=None):
    if seq is None:
        seq = sys.stdin
    for el in seq:
        if type(el) in (str, unicode):el = el.strip()
        if not el: continue
        yield int(el)

def tabulate(seq, transformer = None, sortByValue=False, weight=None):
    result = DefaultDict(int)
    for s in seq:
        n = 1
        if weight: n = weight(s)
        if transformer: s = transformer(s)
        result[s] += n
    return sortItems(result.items(), sortByValue, sortByValue)
    
def parseSection(section):
    """Splits a LexisNexis section into a section and pagenr"""
    if not section: return None
    m = re.match(r'(.*?)(?:pg\.?\s*|blz\.?\s*)(\d+)(.*)', section, re.IGNORECASE)
    #print `section`
    #print ">>>>>>>>>>", m and m.groups()
    #print "<<<<<<<<<<", m and int(m.group(2))
    if not m:
        m = re.match(r'(.*?)(\d+)(.*)', section, re.IGNORECASE)
    if m:
        return (m.group(1) + m.group(3)).strip(), int(m.group(2))
    return None


#simple decorator to cache methods without arguments
def cached(func):
    vals = {}
    def inner(self):
        try:
            id = self.__id__()
        except AttributeError:
            id = self
        if not id in vals:
            vals[id] = func(self)
            #toolkit.warn("Adding [%s] to cache, len now %i" % (id, len(vals)))
        return vals[id]
    inner._vals = vals
    return inner            

def setcached(func, obj, value):
    func._vals[obj] = value

def setCachedProp(obj, propname, value):
    func = obj.__class__.__dict__[propname].fget
    setcached(func, obj, value)

def delCachedProp(obj, propname):
    func = obj.__class__.__dict__[propname].fget
    try:
        id = obj.__id__()
    except AttributeError:
        id = obj
    if id in func._vals:
        del func._vals[id]

def perc(num, denom, decimals):
    if not denom: return "-"
    f = float(num * 100) / denom
    if not decimals: return "%i%%" % int(f)
    return ("%%1.%if%%%%" % decimals) % f

def href(link, text):
    if isIterable(text, True): text = " : ".join(text)
    if link:
        link = "<a href='%s'>%%s</a>" % link
        if text: return link % text
        return link
    return text

def apply(collection, function):
    if isDict(collection): 
        for key in collection:
            collection[key] = function(collection[key])
    else:
        for i, val in enumerate(collection):
            collection[i] = function(val)
    return collection


def format(x, defaultformat="%s", floatformat="%1.3f", intformat="%i"):
    if type(x) == float: return floatformat % x
    if type(x) == int: return intformat % x
    return defaultformat % x

def isnull(x, alt):
    if x is None: return alt
    return x

def naturalSort(list): 
    """ Sort the given list in the way that humans expect. """ 
    return sorted(list, key=naturalSortKey) 
def naturalSortKey(key):
    key = str(key) if type(key) != unicode else key
    convert = lambda text: int(text) if text.isdigit() else text 
    return map(convert, re.split('([0-9]+)', key))


def antiword(wordfile):
    out, err = execute('antiword -', wordfile)
    err = err.replace("I can't find the name of your HOME directory", "")
    if err.strip():
        raise Exception(err)
    try:
        return out.decode('utf-8')
    except:
        return out.decode('latin-1')

def returnTraceback():
    import traceback
    return traceback.format_exc()

def HSVtoHTML(h,s,v):
    rgb = colorsys.hsv_to_rgb(h,s,v)
    return RGBtoHTML(*rgb)

def RGBtoHTML(r,g,b):
    hexcolor = '#%02x%02x%02x' % (r*255,g*255,b*255)
    return hexcolor

def getCaller(depth=2):
    import inspect
    stack = inspect.stack()
    try:
        if len(stack) <= depth:
            return None, None, None
        frame = stack[depth][0]
        try:
            return inspect.getframeinfo(frame)[:3]
        finally:
            del frame
    finally:
        del stack




def getGroup1(regExp, text, flags=re.DOTALL):
    match = re.search(regExp, text, flags)
    if match:
        return match.group(1)
    return None

def prnt(str):
    print str
 
class Counter(collections.defaultdict):
    def __init__(self):
        collections.defaultdict.__init__(self, int)
    def count(self, object, count=1):
        self[object] += count
    def countmany(self, objects):
        if 'keys' in dir(objects):
            for o,c in objects.items():
                self.count(o, count=c)
        else:
            for o in objects:
                self.count(o)
        
    def items(self, reverse=True, byValue=True):
        return sortItems(collections.defaultdict.items(self), reverse=reverse, byValue=byValue)
    def prnt(self, threshold=None, outfunc=prnt, reverse=True, byValue=True):
        for k,v in self.items(reverse=reverse, byValue=byValue):
            if (not threshold) or  v < threshold:
                outfunc("%4i\t%s" % (v, k))
                        
def convertImage(image, informat, outformat=None, quality=None, scale=None):
    cmd = 'convert '
    if scale: cmd += ' -geometry %1.2f%%x%1.2f%% ' % (scale*100, scale*100)
    if quality: cmd += ' -quality %i ' % int(quality*100)
    
    cmd += ' %s:- %s:-' % (informat, outformat or informat)
    out, err = execute(cmd, image)
    if err and err.strip():
        warn(err)
    return out

def splitlist(list, itemsperbatch):
    for i in range(0, len(list), itemsperbatch):
        yield list[i:i+itemsperbatch]

class Indexer(object):
    def __init__(self):
        self.objects = [] # nr -> obj
        self.index = {} # obj -> nr
    def getNumber(self, obj):
        return self.getNumbers(obj)[0]
    def getNumbers(self, *objs):
        result = []
        for obj in objs:
            nr = self.index.get(obj)
            if nr is None:
                nr = len(self.objects)
                self.objects.append(obj)
                self.index[obj] = nr
            result.append(nr)
        return result

def count(seq):
    i = 0
    for dummy in seq: i += 1
    return i
def head(seq):
    for val in seq:
        return val

def getQuoteWords(words):
    if type(words) not in (str, unicode): words = " ".join(words)
    words = re.sub(r'[^\w\s]+', '', words)
    wordset = set(re.split(r'\s+', words.lower()))
    return wordset
    
def quote(words, words_or_wordfilter, quotelen=4, totalwords=25, boldfunc = lambda w : "<em>%s</em>" % w):
    if callable(words_or_wordfilter):
        filt = words_or_wordfilter
    else:
        wordset = getQuoteWords(words_or_wordfilter)
        filt = lambda x: int(x.lower() in wordset)

    positions = {}
    for i, w in enumerate(words):
        if filt(w):
            positions[i] = 0

    default = " ".join(words[:totalwords] + ["..."])
            
    for pos in sorted(positions.keys()):
        nbs = 0
        for w in positions:
            dist = abs(w - pos)
            nbs += int(dist > 0 and dist <= quotelen)
        positions[pos] = nbs
    if not positions: return None
    quotewords = set() # wordids
    boldwords = set()
    while len(quotewords) < totalwords:
        pos, nbs = sortByValue(positions, reverse=True)[0]
        boldwords.add(pos)
        quote = range(max(0, pos - quotelen), min(len(words), pos + quotelen + 1))
        quotewords |= set(quote)
        del positions[pos]
        if not positions: break
    if not quotewords: return None
    lag = -1
    result = []
    quotewords = sorted(quotewords)
    for i in quotewords:
        if i > lag+1: result += ["..."]
        result += [boldfunc(words[i])] if (i in boldwords and boldfunc) else [words[i]]
        lag = i
    if quotewords[-1] <> len(words) - 1:
        result += ["..."]
    
    return " ".join(result)

def ints2ranges(ids):
    start = None
    prev = None
    for i in sorted(ids):
        if start is None: start = i
        elif i > prev + 1:
            yield start, prev
            start = i
        prev = i
    if ids:
        yield start, i

def intselectionTempTable(db, colname, ints, minIntsForTemp=5000):
    if type(ints) not in (set, tuple, list): ints = tuple(ints)
    if len(ints) < minIntsForTemp: return intselectionSQL(colname, ints)
    table = "#intselection_%s" % "".join(chr(random.randint(65,90)) for i in range(25))
    ticker.warn("Creating temp table")
    db.doQuery("CREATE TABLE %s (i int)" % table)
    ticker.warn("Populating temp table")
    db.insertmany(table, "i", [(i,) for i in ints])
    ticker.warn("Done")
    return "(%s in (select i from %s))" % (colname, table)
        
def intselectionSQL(colname, ints, allowtemp=False):
    conds = []
    remainder = []
    for i,j in ints2ranges(ints):
        if j - i > 2: conds.append("(%s between %i and %i)" % (colname, i,j))
        elif j - i == 2: remainder += [str(i), str(i+1), str(j)]
        elif i==j: remainder.append(str(i))
        else: remainder += [str(i),str(j)]
    if remainder: conds.append("(%s in (%s))" % (colname, ",".join(remainder)))
    return "(%s)" % " OR ".join(conds)

def htmlImageObject(bytes, format='png'):
    data = base64.b64encode(bytes)
    return "<object type='image/%s' data='data:image/%s;base64,%s'></object>" % (format, format, data)

class SingletonMeta(type):
    def __init__(cls,name,bases,dic):
        super(Singleton,cls).__init__(name,bases,dic)
        cls.instance=None
    def __call__(cls,*args,**kw):
        if cls.instance is None:
            cls.instance=super(Singleton,cls).__call__(*args,**kw)
        return cls.instance

def filterTrue(seq):
    return (x for x in seq if x)

def multidict(seq):
    """returns a mapping of {key : set(values)} from a sequence of (key, value) tuples with duplicates"""
    result = collections.defaultdict(set)
    if seq:
        for kv in seq:
            if kv:
                k, v = kv
                result[k].add(v)
    return result

def getTermColumns():
    try:
        import termios, fcntl, struct, sys
        
        s = struct.pack("HHHH", 0, 0, 0, 0)
        fd_stdout = sys.stdout.fileno()
        x = fcntl.ioctl(fd_stdout, termios.TIOCGWINSZ, s)
        return struct.unpack("HHHH", x)[1]
    except:
        return None

def buffer(sequence, buffercall, buffersize=100):
    buffer = []
    for s in sequence:
        buffer.append(s)
        if len(buffer) >= buffersize:
            buffercall(buffer)
            for b in buffer: yield b
            buffer = []
    if buffer:
        buffercall(buffer)
        for b in buffer: yield b

def getseq(sequence, seqtypes=(list, tuple, set), pref=list):
    """
    Makes sure that the sequence is a 'proper' sequence (and not
    an iterator/generator). If it is, return the sequence, otherwise
    create a list out of it and return that.
    seqtypes and pref define the allowed sequence types and the preferred
    sequence to make out of it.
    """
    return sequence if isinstance(sequence, seqtypes) else pref(sequence)
        
if __name__ == '__main__':
    process = executepipe("cat")
    pipe = process.next()
    for x in range(200):
        pipe.write("adsfgadfgfdsg")
    print process.next()
    
