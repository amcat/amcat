from __future__ import with_statement

import base64, sbd # only needed for image processing, move to other module>?
import toolkit, config, sys
import re, collections, time
#from oset import OrderedSet # for listeners, replace with proper orderedset whenever python gets it
OrderedSet = set # OrderedSet gaat mis bij pickle, dan maar geen order op de listeners...?
import table3
import threading
import cPickle
from cStringIO import StringIO
from contextlib import contextmanager
import datetime

_encoding = {
    0 : 'utf-8',
    1 : 'UTF-7',
    2 : 'ascii',
    3 : 'latin-1',
}

_MAXTEXTCHARS = 8000

class SQLException(Exception):
    def __init__(self, sql=None, exception=None):
        self.sql = sql
        self.exception = exception
    def __str__(self):
        return"SQLException: Error on executing %r: %s" % (self.sql, self.exception)

def reportDB():
    import MySQLdb
    conf = config.Configuration('app', 'eno=hoty', 'localhost', 'report', MySQLdb)
    db = amcatDB(conf)
    db.conn.select_db('report')
    db.conn.autocommit(False)
    return db


class amcatDB(object):
    """
    Wrapper around a connection to the anoko SQL Server database with a number
    of general and specialized methods to facilitate easy retrieval
    and storage of data
    """

    def __init__(self, configuration=None, auto_commit=0, profile=False, **configargs):
        """
        Initialise the connection to the anoko (SQL Server) database using
        either the given configuration object or config.default
        """
        self.conn = self.connect(configuration, auto_commit, **configargs)
        self.init(profile)
        

    def connect(self, configuration=None, auto_commit=0, **configargs):
        if not configuration: configuration=config.default(**configargs)
        self.dbType = configuration.drivername    
        self.mysql = False #????
        if self.dbType == "MySQLdb":
            import MySQLdb.converters
            conv_dict = MySQLdb.converters.conversions
            conv_dict[0] = float
            conv_dict[246] = float
            conn = configuration.connect(conv=conv_dict)
            conn.select_db('report')
            conn.autocommit(False)
        else:
            conn = configuration.connect()
        self.database = configuration.database
        return conn

    def init(self, profile=False):
        self.DB_LOCK = threading.Lock()        
        self._articlecache = {}
        
        # should be function(string SQL): None or string.
        # Returning string will cause SQL to be changed
        self.beforeQueryListeners = OrderedSet()
        
        # should be function(string SQL, double time, list-of-lists data): None
        self.afterQueryListeners = OrderedSet()

        if profile:
            self.profiler = ProfilingAfterQueryListener()
            self.afterQueryListeners.add(self.profiler)


    ################ picklability #####################
    def __getstate__(self):
        if 'DB_LOCK' in self.__dict__ and self.DB_LOCK:
            self.DB_LOCK.acquire()
        d = dict(self.__dict__.items())
        for delprop in 'DB_LOCK', 'conn':
            if delprop in d: del d[delprop]
        if 'DB_LOCK' in self.__dict__ and self.DB_LOCK:
            self.DB_LOCK.release()
        return d
    def __setstate__(self, d):
        self.__dict__ = d
        self.DB_LOCK = threading.Lock()
      
    def quote(self, value):
        return "'%s'" % str(value).replace("'", "''")   

    ############### cursor acquisition ###############
    
    @contextmanager
    def cursor(self):
        c = None
        try:
            c = self._getCursor()
            yield c
        finally:
            if c is not None:
                self._releaseCursor(c)
        
    def _getCursor(self):
        if self.conn is None:
            raise Exception("Cannot query without database connection")
        if not self.DB_LOCK.acquire(False):
            raise Exception("Cannot lock database, try again later")
        return self.conn.cursor()
    def _releaseCursor(self, cursor):
        if cursor is not None: 
            try:
                cursor.close()
            except:
                pass
        if self.DB_LOCK.locked():
            self.DB_LOCK.release()
        
    def commit(self):
        self.conn.commit()
    def rollback(self):
        self.conn.rollback()

    def queryDict(self, sql, **kargs):
        res, colnames = self.doQuery(sql, colnames=True, **kargs)
        for row in res:
            yield dict(zip(colnames, row))


    ############## Main query logic #####################
    
    def doQueryOnCursor(self, sql, cursor):
        sql  = self.fireBeforeQuery(sql)
        try:
            cursor.execute(sql)
            return cursor
        except Exception, e:
            raise SQLException(sql, e)
            
    def doQuery(self, sql, colnames = False, select=None):
        """
        Execute the query sql on the database and return the result.
        If cursor is given, use that cursor and return the cursor instead
        Otherwise, pre- and postprocess around a call with a new cursor
        """
        if type(sql) == unicode: sql = sql.encode('latin-1', 'replace')
        if select is None:
            select=sql.lower().strip().startswith("select")
        c = None
        t = time.time()
        with self.cursor() as c:
            self.doQueryOnCursor(sql, c)
            try:
                res = c.fetchall() if select else None
            except Exception, e:
                raise SQLException(sql, e)
            self.fireAfterQuery(sql, time.time() - t, res)
            if select and colnames:
                info = c.description
                colnames = [entry[0] for entry in info]
                return res, colnames            
            return res
        
    def doSafeQuery(self, sql, *args):
        e_args = [quotesql(a) for a in args]
        sql = sql % (toolkit.makeList(*e_args))
        self.doQuery(sql)
        

    def doCall(self, proc, params):
        """
        calls the procedure with the given params (tuple). Returns
        (paramvalues, result), where paramvalues is the list of
        params with output params updates, while result is the
        result of c.fetchall() after the call
        """
        c = self.cursor()
        values = c.callproc(proc, params)
        res = c.fetchall()
        c.close()
        return values, res

        
    def fireBeforeQuery(self, sql):
        for func in self.beforeQueryListeners:
            s = func(sql)
            if s: sql = s
        return sql
    def fireAfterQuery(self, sql, time, results):
        for func in self.afterQueryListeners:
            func(sql, time, results)

    def getProfiler(self):
        for l in self.afterQueryListeners:
            if type(l) == ProfilingAfterQueryListener:
                return l
        
            
    def printProfile(self, *args, **kargs):
        l = self.getProfiler()
        if l: l.printreport(*args, **kargs)
            
    def printProfileHTML(self):
        out = StringIO()
        l = self.getProfiler()
        if l: l.printreport(stream=out, htmlgenerator=True)
        return out.getvalue()
    
        
    def update(self, table, col, newval, where):
        self.doQuery("UPDATE %s set %s=%s WHERE (%s)" % (
            table, col, quotesql(newval), where))


    def doInsert(self, sql, retrieveIdent=1):
        """
        Executes the INSERT sql and returns the inserted IDENTITY value
        """
        
            
        self.doQuery(sql)
        if retrieveIdent:
            id = self.getValue("select SCOPE_IDENTITY()")
            if id: id = int(id)
            return id
    
    def escapeFieldName(self, f):
        if self.dbType == "psycopg2":
            return f
        return "[%s]"% f

    def parametermark(self):
        return "%s" if self.dbType == "psycopg2" else "?"
    
    def insert(self, table, dict, idcolumn="For backwards compatibility", retrieveIdent=1):  
        """
        Inserts a new row in <table> using the key/value pairs from dict
        Returns the id value of that table.
        """
        fields = dict.keys()
        values = dict.values()
        fieldsString = ", ".join(map(self.escapeFieldName, fields))
        if False or self.dbType == "psycopg2":
            # use parameters for insert. Test whether this works for mssql as well
            paramstr = ",".join(self.parametermark() for i in range(len(fields)))
            SQL = "INSERT INTO %s (%s) VALUES (%s)" % (table, fieldsString, paramstr)
            if retrieveIdent and self.dbType=="psycopg2": SQL += " RETURNING id"
            with self.cursor() as c:
                #values = map(str, values)
                c.execute(SQL, values)
                if retrieveIdent:
                    if self.dbType == "psycopg2":
                        data = c.fetchall()
                        if data: return data[0][0]
                    
                return
        
        valuesString = ", ".join([quotesql(value) for value in values])
        id = self.doInsert("INSERT INTO %s (%s) VALUES (%s)" % (table, fieldsString, valuesString),
                           retrieveIdent=retrieveIdent)
        return id

    def insertmany(self, table, headers, dataseq):
        if type(dataseq) in (list, tuple) and len(dataseq) == 0: return
        seperator = self.parametermark()
        sql = 'insert into %s (%s) values (%s)' % (table, ','.join(headers), ','.join([seperator] * len(headers)))
        with self.cursor() as c:
            c.executemany(sql, dataseq)
        
        
    def getValue(self, sql):
        data = self.doQuery(sql, select=True)
        if data:
            return data[0][0]
        return None

        
    def getColumn(self, sql, colindex=0, func=None, dbfunc=None):
        for row in self.doQuery(sql):
            val = row[colindex]
            if func: val = func(val)
            elif dbfunc: val = dbfunc(self, val)
            yield val
        
    def article(self, artid):
        #if artid not in self._articlecache:
        #    self._articlecache[artid] = article.Article(self, artid)
        #return self._articlecache[artid]
        import article
        a = article.Article(self, artid)
        return a
                


    
    
    def articles(self, aids=None, tick=False, **kargs):
        if not aids:
            aids = toolkit.intlist(sys.stdin)
        if tick:
            aids = toolkit.tickerate(aids)
        for aid in aids:
            yield self.article(aid)

    
    def exists(self, articleid, type=2, allowempty=True, explain="DEPRECATED"):
        """
        Checks whether a text exists in the database.
        Returns None if the text does not exist at all. If allowempty, returns 'non-null' otherwise.
        If not allowempty, returns 'non-empty' if len(text)>0 and and empty string otherwise.
        Since both None and the empty string evaluate to false, 'if (exists(..))' makes sense usually
        """
        # work with len(cast) to allow len of text and find out exist in one query
        res = self.doQuery("select len(cast(text as varchar(20))) from texts where articleid=%s and type=%s" % (articleid, type))
        if res:
            if allowempty: return "non-null"
            else:
                length = res[0][0]
                if res[0][0] > 0: return "non-empty"
                else: return ""
        else:
            return None  
    

    def _getsources(self):
        """
        Returns a cached sources object. If it does not exist,
        creates and caches it before returning.
        """
        import sources
        if not self._sources:
            self._sources = sources.Sources(self)
        return self._sources
    _sources = None
    sources = property(_getsources)


    @property
    def users(self):
        #TODO get rid of this!
        return user.Users(self)

    def getUser(self):
        import user
        uid = self.getValue("select dbo.anoko_user()")
        return user.User(self, uid)
            
    def newBatch(self, projectid, batchname, query, verbose=0):
        batchid = self.insert('batches', {'projectid':projectid, 'name':batchname, 'query':query})
        return batchid


    def newProject(self, name, description, owner=None, verbose=0):
        name, description = map(quotesql, (name, description))
        owner = int(owner)
        #owner = toolkit.num(owner, lenient=1)
        if toolkit.isString(owner):
            self.doQuery('exec newProject %s, %s, @ownerstr=%s' % (name, description,quotesql(owner)))
        else:
            self.doQuery('exec newProject %s, %s, @ownerid=%s' % (name, description,owner))
            
        return self.getValue('select @@identity')
        
    def createStoredResult(self, name, aids, projectid):
        storedresultid = self.insert('storedresults', {'name':name, 'query':None, 'config':None, 
                                                            'projectid':projectid})
        data = [(storedresultid, int(aid)) for aid in aids]
        self.insertmany('storedresults_articles', ('storedresultid', 'articleid'), data)
        return storedresultid
        
    
    def uploadimage(self, articleid, length, breadth, abovefold, type=None, data=None, filename=None, caption=None):
        """
        Uploads the specified image and links it with the specified article
        Data should be a string containing the binary data.
        If data is None and filename is given, reads the data from that file.
        """
        
        if data is None:
            data = open(filename).read()
            type = filename.split(".")[-1].strip()

        d2 = data
        data = base64.b64encode(data)

        if (d2 != base64.b64decode(data)):
            raise Exception("Data is not invariant under decoding / encoding!")
        
        # create sentence for image
        try:
            p = self.doQuery("SELECT min(parnr) FROM sentences WHERE articleid=%i" % articleid)[0][0]
        except:
            p = None
        
        if p: p = int(p)
        else: p = 1 # if no sentences are present yet

        if p >= 0: newp = -1
        else: newp = p - 1

        ins = {"articleid" : articleid, "parnr" : newp, "sentnr": 1, "sentence" : "[PICTURE]"}
        sid = self.insert("sentences", ins)

        if not sid:
            raise Exception("Could not create sentence")

        if caption:
            for i, line in enumerate(sbd.split(caption)):
                if not line.strip(): continue
                ins = {"articleid" : articleid, "parnr" : newp, "sentnr": 2 + i, "sentence" : line.strip()}
                self.insert("sentences", ins, retrieveIdent=0)

        fold = abovefold and 1 or 0
        ins =  {"sentenceid" : sid, "length" :length, "breadth" : breadth,
                "abovefold" : fold, "imgdata" : data, "imgType" : type}
        self.insert("articles_images", ins, retrieveIdent=0)
        return sid

    def getObjectFactory(self, clas, **kargs):
        return lambda id: clas(self, id, **kargs)

    def getLongText(db, aid, type):
        # workaround to prevent cutting off at texts longer than 65k chars which can crash decoding
        bytes = ""; i=1
        while True:
            add = db.doQuery("select substring(text, %i, %i) from texts where articleid = %i and type = %i" % (i, _MAXTEXTCHARS, aid, type))
            if not add: break
            add = add[0][0]
            bytes += add
            if len(add) < _MAXTEXTCHARS: break
            i += _MAXTEXTCHARS
        return bytes


    def getText(self, aid, type=2):
        sql = "select text, encoding from texts where articleid=%i and type=%i" % (aid, type)
        try:
            txt, enc = self.doQuery(sql)[0]
        except IndexError:
            raise Exception("text not found: articleid=%i and type=%i" % (aid, type))
        if len(txt) > 64000:
            txt = self.getLongText(aid, type)
        return decode(txt, enc)
    
    def setText(self, aid, text, type=2):
        bytes, remainder = None, None
        try:
            bytes = text.encode('ascii')
            print "ASCII encoded!"
        except:
            pass
        
        if not bytes:
            bytes = text.encode('utf-8')
            bytes, remainder = bytes[:7000], bytes[7000:]
            print "%i bytes, %i remainder" % (len(bytes), len(remainder))

        self.doQuery("update texts set text = %s where articleid=%i and type=%i" % (quotesql(bytes.decode('utf-8')), aid, type))
        while remainder:
            bytes, remainder = remainder[:7000], remainder[7000:]
            print "%i bytes, %i remainder" % (len(bytes), len(remainder))
            self.doQuery("exec append_text_bytes @articleid=%i, @data=%s" % (aid, sqlbytes(bytes)))
            
    def updateText(self, aid_or_tid, type_or_None, text):
        if type_or_None is None:
            where = "textid = %i" % aid_or_tid
        else:
            where = "articleid=%i and type=%i" % (aid_or_tid, type_or_None
                                                  )
        text, encoding = encodeText(text)
        text = quotesql(text)
        sql = "update texts set text=%s where %s" % (text, where)
        self.doQuery(sql)
        sql = "update texts set encoding=%i where %s" % (encoding, where)
        self.doQuery(sql)
        return encoding

    def isnull(self):
        return "ifnull" if self.mysql else "isnull"

    _XTYPES = {
        35 : str,
        167 : str,
        175 : str,
        48 : int,
        52 : int,
        56 : int,
        62 : float,
        58 : datetime.datetime,
        61 : datetime.datetime,
        104 : bool,
        }
        
    def getColumnType(self, table, column):
        SQL = """select c.xtype from syscolumns c 
              inner join sysobjects o on c.id = o.id
              where o.name = %s and c.name=%s""" % (
            quotesql(table), quotesql(column))
        xtype = self.getValue(SQL)
        return amcatDB._XTYPES[xtype]

    def getTableColumns(self, table):
        """ do a funky query to obtain column names and xtypes """
        return self.doQuery("""select s.name, t.name from sysobjects o 
        inner join syscolumns s on o.id = s.id 
        inner join systypes t on s.xtype = t.xtype
        where o.name = '%s'
        and s.name not in ('arrowid','sentenceid','codingjob_articleid')
        order by colid""" % table)
    tablecolumn=getTableColumns

    def hasTable(self, name):
        if self.dbType == "psycopg2":
            return self.getValue("SELECT tablename FROM pg_tables WHERE tablename=%s" % quotesql(name))
        elif self.dbType == "sqlite":
            return self.getValue("SELECT name FROM sqlite_master WHERE name=%s" % quotesql(name))
        else:
            return self.getValue("SELECT name FROM sysobjects WHERE xtype='U' and name=%s" % quotesql(name)) 
        raise Exception(self.dbType)

    def intSelectionSQL(self, colname, ints, minIntsForTemp=5000):
        if type(ints) not in (set, tuple, list): ints = tuple(ints)
        if len(ints) < minIntsForTemp:
            conds = []
            remainder = []
            for i,j in toolkit.ints2ranges(ints):
                if j - i > 2: conds.append("(%s between %i and %i)" % (colname, i,j))
                elif j - i == 2: remainder += [str(i), str(i+1), str(j)]
                elif i==j: remainder.append(str(i))
                else: remainder += [str(i),str(j)]
            if remainder: conds.append("(%s in (%s))" % (colname, ",".join(remainder)))
            return "(%s)" % " OR ".join(conds)
        table = "#intselection_%s" % "".join(chr(random.randint(65,90)) for i in range(25))
        self.doQuery("CREATE TABLE %s (i int)" % table)
        self.insertmany(table, "i", [(i,) for i in ints])
        return "(%s in (select i from %s))" % (colname, table)
    
anokoDB = amcatDB


def Articles(**kargs):
    db = anokoDB()
    return db.articles(**kargs)
        
        
def decode(text, encodingid, lenient=True):
    if type(text) == unicode:
        return text
    if not text: return text # avoid problem with None that does not have the decode function
    if encodingid is None: encodingid = 3 # assume latin-1
    try:
        return text.decode(_encoding[encodingid])
    except  UnicodeDecodeError:
       return text.decode('latin-1')

class RawSQL(object):
    def __init__(self, sql):
        self.sql = sql

def sqlbytes(bytes):
    return "0x%s" % bytes.encode('hex')

ENCODE_UTF8 = False
def quotesql(strOrSeq):
    """
    if str is seq: return tuple of quotesql(values)
    if str is string: escapes any quotes and backslashes in the string and returns the string in quotes
    otherwise: coerce to str and recurse.
    """
    #print `strOrSeq`, ENCODE_UTF8
    if type(strOrSeq) == buffer:
        strOrSeq = str(strOrSeq)
    if strOrSeq is None:
        return 'null'
    elif isinstance(strOrSeq, RawSQL):
        return strOrSeq.sql
    elif toolkit.isDate(strOrSeq):
        return "'%s'" % toolkit.writeDateTime(strOrSeq)
    elif type(strOrSeq) == unicode and ENCODE_UTF8:
        try:
            ascii = strOrSeq.encode('ascii')
            ascii = re.sub("'", "''", ascii)
            return "'%s'" % ascii
        except:
            bytes = strOrSeq.encode('utf-8')
            if len(bytes) > 7900:
                raise Exception("Cannot directly insert utf-8 bytes longer than 7900 bytes")
            return "cast(%s as varchar(8000))" % sqlbytes(bytes)
    elif type(strOrSeq) in (str, unicode):
        if type(strOrSeq) == unicode:
            strOrSeq = strOrSeq.encode('latin-1')
        strOrSeq = strOrSeq.replace("\r\n","\n")
        strOrSeq = strOrSeq.replace("\n\r","\n")
        strOrSeq = strOrSeq.replace("\r","\n")
        strOrSeq = strOrSeq.replace("\x00","")
        #if self.dbType <> "psycopg2" and (not checklatin1(strOrSeq)):
        #    raise Exception("Offered bytes (or latin-1 encoded unicode) %r not in safe subset!" % strOrSeq)
        strOrSeq = re.sub("'", "''", strOrSeq)
        return "'%s'" % strOrSeq
    elif toolkit.isSequence(strOrSeq):
        return tuple(map(quotesql, strOrSeq))
    elif type(strOrSeq) == bool:
        return strOrSeq and "1" or "0"
    elif type(strOrSeq) == int:
        return str(strOrSeq)
    else:
        return quotesql(str(strOrSeq))

def checklatin1(txt, verbose=False):
    for p, c in enumerate(txt):
        i = ord(c)
        if (i < 0x20 or (i > 0x7e and i < 0xa0) or i > 0xff) and i not in (0x0a,0x09):
            if verbose: toolkit.warn("Character %i (%r) at position %i is not latin-1" % (i, c, p))
            return False
    return True


def encodeText(text):
    if type(text) <> unicode:
        text = text.decode('latin-1')
    try:
        txt = text.encode('ascii')
        return txt, 2
    except UnicodeEncodeError: pass
    try:
        txt = text.encode('latin-1')
        if checklatin1(txt):
            return txt, 3
    except UnicodeEncodeError: pass
    txt = text.replace('\r', '\n')
    txt = text.replace(u'\x07', '')
    txt = txt.encode('utf-7')
    return txt, 1

    
def encode(s, enc):
    if s is None: return s
    if type(s) <> unicode: s = s.decode('latin-1')
    return s.encode(_encoding[enc])

    
def encodeTexts(texts):
    encoding = 2
    for text in texts:
        if not text: continue
        t, enc = encodeText(text)
        if enc==1:
            encoding = 1
            break
        if enc==3: encoding = 3
    return [encode(t, encoding) for t in texts], encoding

def doreplacenumbers(sql):
    sql = re.sub(r"\d[\d ,]*", "# ", sql)
    sql = re.sub(r"'#['#, ]*'", "'#' ", sql)
    sql = sql.replace("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED","")
    sql = sql.replace("SET TRANSACTION ISOLATION LEVEL READ COMMITTED","")
    sql = re.sub("\s+", " ", sql)

    return sql.strip()

class ProfilingAfterQueryListener(object):
    def __init__(self):
        self.queries = collections.defaultdict(list)
    def __call__(self, query, time, resultset):
        #print ">>>", query, time, len(resultset)
        l = len(resultset) if resultset else 0
        self.queries[query].append((time, l))
    def printreport(self, sort="time", stream=sys.stdout, useunicode=True, htmlgenerator=False, encoding="utf-8", clear=True, *args, **kargs):
        data = self.reportTable(*args, **kargs)
        if sort:
            if type(sort) in (str, unicode): sort = sort.lower()
            for col in data.getColumns():
                if col == sort or col.id == sort or col.label.lower() == sort:
                    data = table3.SortedTable(data, (col, False))
        import tableoutput
        if htmlgenerator:
            if htmlgenerator is True: htmlgenerator = tableoutput.HTMLGenerator()
            htmlgenerator.generate(data, stream)
        else:
            result = tableoutput.table2unicode(data, formats=["%s", "%s", "%1.5f", "%1.5f", "%4.1f"], useunicode=useunicode)
            if type(result) == unicode: result = result.encode(encoding)
            print >>stream, result
        if clear:         self.queries = collections.defaultdict(list)
    def reportTable(self, *args, **kargs):
        return table3.ListTable(self.report(*args, **kargs), ["Query", "N", "Time", "AvgTime", "AvgLen"])
    def report(self, replacenumbers=True, maxsqlen=100):
        data = collections.defaultdict(lambda : [0, 0., 0]) # {sql : [n, totaltime, totallength]}
        for sql, timelens in self.queries.iteritems():
            if replacenumbers: sql = doreplacenumbers(sql)
            if len(sql) > maxsqlen: sql = sql[:maxsqlen-2]+".."
            sql = `sql`
            for time, length in timelens:
                data[sql][0] += 1
                data[sql][1] += time
                data[sql][2] += length
        data = [(s, n, t, t/n, float(l)/n) for (s, (n,t,l)) in data.iteritems()]
        return data

def persistent_id(obj):
    if type(obj) == amcatDB:
        return "dbtoolkit.py::amcatDB"

def get_persistent_load(db):
    def persistent_load(id):
        if id == "dbtoolkit.py::amcatDB":
            return db
        raise Exception("Unknown persistent id: %r" % id)
    return persistent_load
    
def persistent_dumps(obj, module=cPickle):
    s = StringIO()
    p = module.Pickler(s)
    p.persistent_id = persistent_id
    p.dump(obj)
    return s.getvalue()
    
def persistent_loads(bytes, db, module=cPickle):
    s = StringIO(bytes)
    u = module.Unpickler(s)
    u.persistent_load = get_persistent_load(db)
    return u.load()






# intselectionTempTable = intSelection
       

    
if __name__ == '__main__':
    db = anokoDB()
    db.beforeQueryListeners.append(toolkit.warn)
    p = ProfilingAfterQueryListener()
    db.afterQueryListeners.append(p)
    db.doQuery("select top 10 * from articles")
    db.doQuery("select top 15 * from articles")
    db.doQuery("select top 10 * from articles")
    db.doQuery("select top 10 * from projects")

    print
    p.printreport()

    
