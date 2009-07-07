import base64, sys
import toolkit, config, sbd
import article, sources, user
from toolkit import cached

_debug = toolkit.Debug('dbtoolkit',2)

_encoding = {
    1 : 'UTF-7',
    2 : 'ascii',
    3 : 'latin-1',
}

_MAXTEXTCHARS = 8000
    
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

    def __init__(self, configuration=None, auto_commit=0):
        """
        Initialise the connection to the anoko (SQL Server) database using
        either the given configuration object or config.default
        """
        
        if not configuration:
            configuration=config.default()
        self.dbType = configuration.drivername
        
        _debug(3,"Connecting to database '%(database)s' on '%(username)s@%(host)s' using driver %(drivername)s... " % configuration.__dict__, 0)
        self.conn = configuration.connect()# datetime="mx", auto_commit=auto_commit)
        _debug(3,"OK!", 2)

        self._articlecache = {}
        
        self.mysql = False
        
        if self.dbType == "MySQLdb":
            import MySQLdb.converters
            conv_dict = MySQLdb.converters.conversions
            conv_dict[0] = float
            conv_dict[246] = float
            self.conn = configuration.connect(conv=conv_dict)
            self.conn.select_db('report')
            self.conn.autocommit(False)
        else:
            self.conn = configuration.connect()
        
      
    def quote(self, value):
        return "'%s'" % str(value).replace("'", "''")   
        
        
        
    def cursor(self):
        return self.conn.cursor()
        
        
    def commit(self):
        self.conn.commit()

        
    def doQuery(self, sql, cursor = None, colnames = False, select=None):
        """
        Execute the query sql on the database and return the result.
        If cursor is given, use that cursor and return the cursor instead
        """
        #import time
        #print "%10.5f : %s" % (time.time(), sql)
        c = None
        if select is None:
            select=sql.lower().strip().startswith("select")
        _debug(5,sql)
        if select:
            _debug(4,"selecting: %s... " % sql[:10].replace('\n',' '), 0)
        else:
            _debug(4,"executing: %s... " % sql[:10].replace('\n',' '), 0)
        try:
            if cursor:
                cursor.execute(sql)
                _debug.ok(4)
                return cursor
            else:
                #if colnames:
                    c = self.cursor()
                    if type(sql) == unicode:
                        c.execute(sql.encode('latin-1', 'replace'))
                    else:
                        c.execute(sql)
                    if not select:
                        _debug.ok(4)
                        return
                    res = c.fetchall()
                    if colnames:
                        info = c.description
                        colnames = [entry[0] for entry in info]
                        _debug.ok(4)
                        return res, colnames
                    else:
                        _debug.ok(4)
                        return res
                #else:
                #    res = self.conn.execute(sql)
                #    _debug.ok(4)
                #    if res:
                #        return res[0]
        except Exception, details:
            _debug.fail(4)
            _debug(1,"Error while executing: "+sql)
            if c:
                c.close()
            raise details
            
            
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

        
    def update(self, table, col, newval, where):
        self.doQuery("UPDATE %s set %s=%s WHERE (%s)" % (
            table, col, toolkit.quotesql(newval), where))


    def doInsert(self, sql, retrieveIdent=1):
        """
        Executes the INSERT sql and returns the inserted IDENTITY value
        """
        _debug(4, "Inserting new value")
        self.doQuery(sql)
        _debug(4, "Retrieving SCOPE_IDENTITY")
        if not retrieveIdent: return
        res = self.doQuery("select SCOPE_IDENTITY()")
        _debug(4, "Extracting SCOPE_IDENTITY from %s" % res)
        try:
            id = int(res[0][0])
        except Exception, details:
            _debug(2,"Could not retrieve identity value?")
            _debug(2,details)
            id=None
        return id    
    
    
    def insert(self, table, dict, idcolumn="For backwards compatibility", retrieveIdent=1):  
        """
        Inserts a new row in <table> using the key/value pairs from dict
        Returns the id value of that table.
        """
        fields = dict.keys()
        values = dict.values()
        fieldsString = ", ".join(fields)
        def quote(x):
            if type(x) == bool: x = int(x)
            if x:
                if type(x) == unicode:
                    x = x.encode('latin-1')
                else:
                    x = str(x).decode('latin-1').encode('latin-1') # make sure the string is in latin-1 else query will fail anyway, right?
            return toolkit.quotesql(x)
        quoted = [quote(value) for value in values]
        valuesString = ", ".join(quoted)
        id = self.doInsert("INSERT INTO %s (%s) VALUES (%s)" % (table, fieldsString, valuesString),
                           retrieveIdent=retrieveIdent)
        return id

    def insertmany(self, table, headers, dataseq):
        if len(dataseq) == 0: return
        seperator = '%s' if self.dbType == 'MySQLdb' else '?'
        sql = 'insert into %s (%s) values (%s)' % (table, ','.join(headers), ','.join([seperator] * len(headers)))
        self.cursor().executemany(sql, dataseq)
        
        
    def getValue(self, sql):
        data = self.doQuery(sql)
        if data:
            return data[0][0]
        return None

        
    def getColumn(self, sql, colindex=0):
        for col in self.doQuery(sql):
            yield col[colindex]
        

        
    def article(self, artid):
        """
        Builds an Article object from the database
        """
        if artid not in self._articlecache:
            self._articlecache[artid] = article.fromDB(self, artid)
        return self._articlecache[artid]
    
    
    def articles(self, aids=None):
        if not aids:
            aids = toolkit.intlist(sys.stdin)
        for a in article.Articles(aids, self):
            yield a

    
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
        if not self._sources:
            self._sources = sources.Sources(self)
        return self._sources
    _sources = None
    sources = property(_getsources)


    @property
    @cached
    def users(self):
        return user.Users(self)

        
            
    def newBatch(self, projectid, batchname, query, verbose=0):
        batchid = self.insert('batches', {'projectid':projectid, 'name':batchname, 'query':query})
        _debug(4-3*verbose,"Created new batch with id %d" % batchid)
        return batchid


    def newProject(self, name, description, owner=None, verbose=0):
        name, description = map(toolkit.quotesql, (name, description))
        owner = toolkit.num(owner, lenient=1)
        if toolkit.isString(owner):
            self.doQuery('exec newProject %s, %s, @ownerstr=%s' % (name, description,toolkit.quotesql(owner)))
        else:
            self.doQuery('exec newProject %s, %s, @ownerid=%s' % (name, description,owner))
            
        res = self.doQuery('select @@identity')
        try:
            id = int(res[0][0])
        except Exception, details:
            _debug(2,"Could not retrieve identity value?")
            _debug(2,details)
            id=None

        _debug(4-3*verbose,"Created new project with id %s" % id)
        return id

        
    def createStoredResult(self, name, aids, projectid):
        storedresultid = self.insert('storedresults', {'name':name, 'query':None, 'config':None, 
                                                            'projectid':projectid})
        data = [(storedresultid, int(aid)) for aid in aids]
        self.insertmany('storedresults_articles', ('storedresultid', 'articleid'), data)
        return storedresultid
        
    '''
    def updateProject(self, projectid, newName=None, newDescription=None, newOwner=None):
        params=['@id=%d'%projectid]
        if newName: params.append('@newname=%s' % toolkit.quotesql(newName))
        if newDescription: params.append('@newdescription=%s' % toolkit.quotesql(newDescription))
        if newOwner: params.append('@newowner=%d' % newOwner)
        if len(params)==1: raise Exception('Nonsensical call of updateProject without changes')
        
        self.doQuery('exec updateProject %s' % (', '.join(params)))


    def updateBatch(self, batchid, newName=None, newProject=None):
        params=['@id=%d'%batchid]
        if newName: params.append('@newname=%s' % toolkit.quotesql(newName))
        if newProject: params.append('@newproject=%d' % newProject)
        if len(params)==1: raise Exception('Nonsensical call of updatBatch without changes')

        self.doQuery('exec updateBatch %s' % (', '.join(params)))

        
    def deleteBatch(self, batchid):
        params=['@id=%d'%batchid]
        self.doQuery('exec deleteBatch %s' % (', '.join(params)))
        
        
    def deleteProject(self, projectid):
        params=['@id=%d'%projectid]
        self.doQuery('exec deleteProject %s' % (', '.join(params)))

        
    def createCodingJob(self, jobname, coderid, aids):
        jobid = self.insert("codingjobs", {'name':jobname, 'coder_userid':coderid})
        for aid in aids:
            self.insert("codingjobs_articles", {'codingjobid':jobid, 'articleid':aid}, retrieveIdent=0)
        return jobid
    '''


    '''
    def isMyProject(self, projectid):
        query = "select dbo.anoko_user()-ownerid from projects where projectid=%s"  % projectid
        res = self.doQuery(query)
        if not res: return None
        if res[0][0]==0: return True
        return False
        
    def returnAnokoUsers(self):
        query = """SELECT userid
        from sysmembers s
        inner join sysusers i on s.memberuid = i.uid
        inner join users u on i.name = u.username
        where groupuid=16400"""
        data = self.doQuery(query)
        return [item[0] for item in data]
        
    def getProjectInfo(self, projectid=None):
        if projectid=="-s":
            query = "select projectid, ownerid, name from projects"
        elif projectid=="-d":
            query = "select projectid, name, ownerid, description, convert(varchar,insertdate,105) as insertdate from projects"
        elif projectid[:2]=="-e":
            query = "select projectid, ownerid, name, description, convert(varchar,insertdate,105) as insertdate from projects where projectid=%s" % projectid[3:]
        elif projectid:
            query = "select * from vw_batches_counts where projectid=%s" % projectid
        else:
            query = "select * from vw_batches"

        return self.doQuery(query, colnames=1)

    def projectList(self, owner=0, projectid=None, colnames=1, detailed=1):
        where = []
        if owner: where.append("ownerid = dbo.anoko_user()")
        if projectid: where.append("projectid = %s" % projectid)
        if detailed:
            query = "SELECT projectid, name, description, owner, convert(varchar,insertdate,105) as insertdate FROM vw_projectinfo"
        else:
            query = "SELECT projectid, name, ownerid FROM projects"
            
        if where:
            query += " WHERE " + " AND ".join(where)
        return self.doQuery(query, colnames=colnames)
        
    def getProjectName(self, projectid):
        query = "select name from projects where projectid=%s" % projectid
        data = self.doQuery(query, colnames=0)
        if data:
            return data[0][0]
        return None
        
    def getSelections(self, owner=0):
        if owner != 0:
            where =  'where ownerid = %s' % owner
        else:
            where = ''
        query = "SELECT storedresultid, name, ownerid FROM storedresults %s" % where
        return self.doQuery(query, colnames=0)
        
    def getCodingJobs(self, own=0, detailed=0, colnames=1, jobid=None):
        where = []
        if own:
            where.append("owner_userid = dbo.anoko_user()")
        if jobid:
            where.append("codingjobid = %s" % jobid)
        where = where and (" WHERE " + " AND ".join(where)) or ''
        if detailed:
            if jobid:
                extraSelect = ', codingjobs.unitschemaid, codingjobs.articleschemaid'
            else:
                extraSelect = ''
            query = """SELECT codingjobs.codingjobid, codingjobs.name, users.username, codingjobs.insertdate %s
                        FROM codingjobs
                        INNER JOIN users
                        ON users.userid = codingjobs.owner_userid
                        %s
                        ORDER BY codingjobs.codingjobid DESC""" % (extraSelect, where)
        else:
            query = """SELECT codingjobid, name, owner_userid
                        FROM codingjobs
                        %s
                        ORDER BY codingjobid DESC""" % where
        return self.doQuery(query, colnames=colnames)
        
        
    def getCodingJobSets(self, codingjobid, setnr=None):
        wherestr = ' AND setnr = %s' % setnr if setnr else ''
        query = """SELECT setnr, username as coder, count(articleid) articles, 
                        sum(ISNULL(CAST(irrelevant as INTEGER), 0)) irrelevant,
                        sum(has_arrow) 'with arrows', sum(done) done
        FROM vw_codingjobs_articles_done
        WHERE codingjobid=%s
        %s
        GROUP BY setnr, username
        ORDER BY setnr""" % (codingjobid, wherestr)
        return self.doQuery(query, colnames=1)
        
    def isMyCodingJob(self, codingjobid):
        query = "SELECT dbo.anoko_user()-owner_userid FROM codingjobs WHERE codingjobid=%s" % codingjobid
        data = self.doQuery(query, colnames=0)
        if not data:
            return None
        if data[0][0] == 0:
            return True
        return False
        
    def getCoder(self, codingjobid, setnr):
        query = 'SELECT coder_userid FROM codingjobs_sets WHERE codingjobid=%s AND setnr=%s' % \
                                                                                    (codingjobid, setnr)
        data = self.doQuery(query, colnames=0)
        if data:
            return data[0][0]
        else:
            return None
    '''
        
    '''   
    def changeCoder(self, codingjobid, setnr, coderid):
        params=['@jobid=%d'%codingjobid]
        params.append('@setnr=%d'%setnr)
        params.append('@newcoderid=%d'%coderid)
        self.doQuery('exec changecodingjobsetcoder %s' % (', '.join(params)))
    
    def changeJobOwner(self, codingjobid, ownerid):
        params=['@jobid=%d'%codingjobid]
        params.append('@newownerid=%d'%ownerid)
        self.doQuery('exec changecodingjobowner %s' % (', '.join(params)))
        
    def deleteJob(self, codingjobid):
        params=['@jobid=%d'%codingjobid]
        self.doQuery('exec deletecodingjob %s' % (', '.join(params)))
        
    def deleteCodingSet(self, codingjobid, setnr):
        params=['@jobid=%d'%codingjobid]
        params.append('@setnr=%d'%setnr)
        self.doQuery('exec deletecodingjob_set %s' % (', '.join(params)))
    '''
    
    
    '''
    def getSelectionInfo(self, selectionid):
        query = "SELECT query, config FROM storedresults where storedresultid = %s" % selectionid
        return self.doQuery(query, colnames=0)
        
    def batchList(self, projectid, colnames=1):
        query = """SELECT batchid, batch as batchname, project, narticles as articles 
                    FROM vw_batches_counts
                    WHERE projectid=%s and batchid is not null
                    ORDER BY batchid""" % projectid
        return self.doQuery(query, colnames=colnames)
        
    def getBatchInfo(self, batchid, details=None):
        if details:
            extra = ', project' 
        else:
            extra = ''
        query = "select batchid, batch as batchname, projectid, owner%s from vw_batches_counts where batchid=%s" % (extra,batchid)
        return self.doQuery(query, colnames=1)

    """def returnUserSelect(self, currentOwner=0, multiple=0, name="ownerid"):
        html = '<select name=%s %s>' % (name, multiple and 'multiple size=10' or '')
        data = self.doQuery('select userid, fullname from users')
        for userid, fullname in data:
            if userid == currentOwner:
                html += '<option value="%s" selected>%s</option>' % (userid,fullname)
            else:
                html += '<option value="%s">%s</option>' % (userid,fullname)
        html += '</select>'
        return html"""
        
    def getIndices(self, colnames=0, done=1, started=1):
        query = """SELECT directory, indexid, name, owner_userid
                    FROM indices
                    WHERE done = %(done)s AND started = %(started)s
                    ORDER BY indexid DESC""" % locals()
        data = self.doQuery(query, colnames=colnames)
        return [ (row[0], '%s - %s' % (row[1], row[2]), row[3]) for row in data]
        
    def getUserList(self):
        return self.doQuery('SELECT userid, fullname FROM users ORDER BY fullname', colnames=0)

    def getUserInitials(self, userid):
        return self.getValue('SELECT initials FROM users WHERE userid=%i' % userid)
    '''
    

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


    def getText(self, aid, type):
        sql = "select text, encoding from texts where articleid=%i and type=%i" % (aid, type)
        try:
            txt, enc = self.doQuery(sql)[0]
        except IndexError:
            raise Exception("text not found: articleid=%i and type=%i" % (aid, type))
        if len(txt) > 64000:
            txt = self.getLongText(aid, type)
        return decode(txt, enc)

        
    def updateText(self, aid_or_tid, type_or_None, text):
        if type_or_None is None:
            where = "textid = %i" % aid_or_tid
        else:
            where = "articleid=%i and type=%i" % (aid_or_tid, type_or_None
                                                  )
        text, encoding = encodeText(text)
        text = toolkit.quotesql(text)
        sql = "update texts set text=%s where %s" % (text, where)
        self.doQuery(sql)
        sql = "update texts set encoding=%i where %s" % (encoding, where)
        self.doQuery(sql)
        return encoding

    def isnull(self):
        return "ifnull" if self.mysql else "isnull"

    def tablecolumns(self, table):
        """ do a funky query to obtain column names and xtypes """
        return self.doQuery("""select s.name, t.name from sysobjects o 
        inner join syscolumns s on o.id = s.id 
        inner join systypes t on s.xtype = t.xtype
        where o.name = '%s'
        and s.name not in ('arrowid','sentenceid','codingjob_articleid')
        order by colid""" % table)
         
anokoDB = amcatDB


def Articles(**kargs):
    db = anokoDB()
    return db.articles(**kargs)
        
        
def decode(text, encodingid):
    if not text: return text # avoid problem with None that does not have the decode function
    if not encodingid: encodingid = 3 # assume latin-1
    return text.decode(_encoding[encodingid])

def checklatin1(txt):
    for p, c in enumerate(txt):
        i = ord(c)
        if (i < 0x20 or (i > 0x7e and i < 0xa0) or i > 0xff) and i not in (0x0a,0x09):
            #toolkit.warn("Character %i (%r) at position %i is not latin-1" % (i, c, p))
            return False
    return True


def encodeText(text):
    if type(text) <> unicode:
        text = text.decode('latin-1')
    try:
        txt = text.encode('ascii')
        return txt, 2
    except UnicodeEncodeError, e: pass
    try:
        txt = text.encode('latin-1')
        if checklatin1(txt):
            return txt, 3
    except UnicodeEncodeError, e: pass
    txt = text.encode('utf-7')
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

if __name__ == '__main__':
    #print "Opening connection with database"
    #db = anokoDB()
    #print "Trying to upload image from sys.argv[1] for article sys.argv[2] with optional caption sys.argv[3]"
    #import sys
    #caption = None
    #if len(sys.argv) > 3:
    #    caption = sys.argv[3]
    #db.uploadimage(int(sys.argv[2]), 0, 0, 0, filename=sys.argv[1], caption=caption)
    #print "Reading project name"
    #print db.doQuery("select top 1 * from projects")
    print encodeTexts([u'abc\xe8', u'def'])
    
