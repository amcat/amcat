#!/bin/env python2.2

import sbd
import toolkit
import base64
import config
import article
import sources

_debug = toolkit.Debug('dbtoolkit',2)

def Articles(**kargs):
    db = anokoDB()
    return db.articles(**kargs)

class anokoDB(object):
    """
    Wrapper around a connection to the anoko SQL Server database with a number
    of general and specialized methods to facilitate easy retrieval
    and storage of data
    """

    def __init__(this, configuration=None, auto_commit=1):
        """
        Initialise the connection to the anoko (SQL Server) database using
        either the given configuration object or config.default
        """
        
        if not configuration:
            configuration=config.default()
        
        _debug(3,"Connecting to database '%(database)s' on '%(username)s@%(host)s' using driver %(drivername)s... " % configuration.__dict__, 0)
        this.conn = configuration.connect()# datetime="mx", auto_commit=auto_commit)
        _debug(3,"OK!", 2)

        this._articlecache = {}


    def _getsources(this):
        """
        Returns a cached sources object. If it does not exist,
        creates and caches it before returning.
        """
        if not this._sources:
            this._sources = sources.Sources(this)
        return this._sources
    _sources = None
    sources = property(_getsources)

    def cursor(this):
        return this.conn.cursor()

    def doQuery(this, sql, cursor = None, colnames = False, select=None):
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
                    c = this.cursor()
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
                #    res = this.conn.execute(sql)
                #    _debug.ok(4)
                #    if res:
                #        return res[0]
        except Exception, details:
            _debug.fail(4)
            _debug(1,"Error while executing: "+sql)
            if c:
                c.close()
            raise details
            
    def doCall(this, proc, params):
        """
        calls the procedure with the given params (tuple). Returns
        (paramvalues, result), where paramvalues is the list of
        params with output params updates, while result is the
        result of c.fetchall() after the call
        """
        c = this.cursor()
        values = c.callproc(proc, params)
        res = c.fetchall()
        c.close()
        return values, res


    def doInsert(this, sql, retrieveIdent=1):
        """
        Executes the INSERT sql and returns the inserted IDENTITY value
        """
        _debug(4, "Inserting new value")
        this.doQuery(sql)
        _debug(4, "Retrieving SCOPE_IDENTITY")
        if not retrieveIdent: return
        res = this.doQuery("select SCOPE_IDENTITY()")
        _debug(4, "Extracting SCOPE_IDENTITY from %s" % res)
        try:
            id = int(res[0][0])
        except Exception, details:
            _debug(2,"Could not retrieve identity value?")
            _debug(2,details)
            id=None
        return id

    def article(this, artid, type=2):
        """
        Builds an Article object from the database
        """
        if (artid, type) not in this._articlecache:
            this._articlecache[artid, type] = article.fromDB(this, artid, type)
        return this._articlecache[artid, type]

    def update(this, table, col, newval, where):
        this.doQuery("UPDATE %s set %s=%s WHERE (%s)" % (
            table, col, toolkit.quotesql(newval), where))
    
    def insert(this, table, dict, idcolumn="For backwards compatibility", retrieveIdent=1):  
        """
        Inserts a new row in <table> using the key/value pairs from dict
        Returns the id value of that table.
        """
        fields = dict.keys()
        values = dict.values()
        fieldsString = ", ".join(fields)
        valuesString = ", ".join(map(toolkit.quotesql, values)) 
        id = this.doInsert("INSERT INTO %s (%s) VALUES (%s)" % (table, fieldsString, valuesString),
                           retrieveIdent=retrieveIdent)
        return id

    def newBatch(this, projectid, batchname, query, verbose=0):
        batchid = this.insert('batches', {'projectid':projectid, 'name':batchname, 'query':query})
        _debug(4-3*verbose,"Created new batch with id %d" % batchid)
        return batchid


    def newProject(this, name, description, owner=None, verbose=0):
        name, description = map(toolkit.quotesql, (name, description))
        owner = toolkit.num(owner, lenient=1)
        if toolkit.isString(owner):
            this.doQuery('exec newProject %s, %s, @ownerstr=%s' % (name, description,toolkit.quotesql(owner)))
        else:
            this.doQuery('exec newProject %s, %s, @ownerid=%s' % (name, description,owner))
            
        res = this.doQuery('select @@identity')
        try:
            id = int(res[0][0])
        except Exception, details:
            _debug(2,"Could not retrieve identity value?")
            _debug(2,details)
            id=None

        _debug(4-3*verbose,"Created new project with id %s" % id)
        return id

    def updateProject(this, projectid, newName=None, newDescription=None, newOwner=None):
        params=['@id=%s'%projectid]
        if newName: params.append('@newname=%s' % toolkit.quotesql(newName))
        if newDescription: params.append('@newdescription=%s' % toolkit.quotesql(newDescription))
        if newOwner: params.append('@newowner=%s' % newOwner)
        if len(params)==1: raise Exception('Nonsensical call of updateProject without changes')
        
        this.doQuery('exec updateProject %s' % (', '.join(params)))


    def updateBatch(this, batchid, newName=None, newProject=None):
        params=['@id=%s'%batchid]
        if newName: params.append('@newname=%s' % toolkit.quotesql(newName))
        if newProject: params.append('@newproject=%s' % newProject)
        if len(params)==1: raise Exception('Nonsensical call of updatBatch without changes')

        this.doQuery('exec updateBatch %s' % (', '.join(params)))

    def deleteBatch(this, batchid):
        params=['@id=%s'%batchid]
        this.doQuery('exec deleteBatch %s' % (', '.join(params)))
        
    def deleteProject(this, projectid):
        params=['@id=%s'%projectid]
        this.doQuery('exec deleteProject %s' % (', '.join(params)))

    def createCodingJob(this, jobname, coderid, aids):
        jobid = this.insert("codingjobs", {'name':jobname, 'coder_userid':coderid})
        for aid in aids:
            this.insert("codingjobs_articles", {'codingjobid':jobid, 'articleid':aid}, retrieveIdent=0)
        return jobid
        

    def exists(this, articleid, type=2, allowempty=True, explain="DEPRECATED"):
        """
        Checks whether a text exists in the database.
        Returns None if the text does not exist at all. If allowempty, returns 'non-null' otherwise.
        If not allowempty, returns 'non-empty' if len(text)>0 and and empty string otherwise.
        Since both None and the empty string evaluate to false, 'if (exists(..))' makes sense usually
        """
        # work with len(cast) to allow len of text and find out exist in one query
        res = this.doQuery("select len(cast(text as varchar(20))) from texts where articleid=%s and type=%s" % (articleid, type))
        if res:
            if allowempty: return "non-null"
            else:
                length = res[0][0]
                if res[0][0] > 0: return "non-empty"
                else: return ""
        else:
            return None


    def articles(this, **kargs):
        import sys
        return article.Articles(sys.stdin, this, **kargs)

    def isMyProject(this, projectid):
        query = "select dbo.anoko_user()-ownerid from projects where projectid=%s"  % projectid
        res = this.doQuery(query)
        if not res: return None
        if res[0][0]==0: return True
        return False
        
    def returnAnokoUsers(this):
        query = """SELECT userid
        from sysmembers s
        inner join sysusers i on s.memberuid = i.uid
        inner join users u on i.name = u.username
        where groupuid=16400"""
        data = this.doQuery(query)
        return [item[0] for item in data]
        
    def getProjectInfo(this, projectid=None):
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

        return this.doQuery(query, colnames=1)

    def projectList(this, owner=0, projectid=None, colnames=1, detailed=1):
        where = []
        if owner: where.append("ownerid = dbo.anoko_user()")
        if projectid: where.append("projectid = %s" % projectid)
        if detailed:
            query = "SELECT projectid, name, description, owner, convert(varchar,insertdate,105) as insertdate FROM vw_projectinfo"
        else:
            query = "SELECT projectid, name, ownerid FROM projects"
            
        if where:
            query += " WHERE " + " AND ".join(where)
        return this.doQuery(query, colnames=colnames)
        
    def getProjectName(this, projectid):
        query = "select name from projects where projectid=%s" % projectid
        data = this.doQuery(query, colnames=0)
        if data:
            return data[0][0]
        return None
        
    def getSelections(this, owner=0):
        if owner != 0:
            where =  'where ownerid = %s' % owner
        else:
            where = ''
        query = "SELECT storedresultid, name, ownerid FROM storedresults %s" % where
        return this.doQuery(query, colnames=0)
        
    def getCodingJobs(this, own=0, detailed=0, colnames=1, jobid=None):
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
        return this.doQuery(query, colnames=colnames)
        
        
    def getCodingJobSets(this, codingjobid, setnr=None):
        wherestr = ' AND setnr = %s' % setnr if setnr else ''
        query = """SELECT setnr, username as coder, count(articleid) articles, 
                        sum(ISNULL(CAST(irrelevant as INTEGER), 0)) irrelevant,
                        sum(has_arrow) 'with arrows', sum(done) done
        FROM vw_codingjobs_articles_done
        WHERE codingjobid=%s
        %s
        GROUP BY setnr, username
        ORDER BY setnr""" % (codingjobid, wherestr)
        return this.doQuery(query, colnames=1)
        
    def isMyCodingJob(this, codingjobid):
        query = "SELECT dbo.anoko_user()-owner_userid FROM codingjobs WHERE codingjobid=%s" % codingjobid
        data = this.doQuery(query, colnames=0)
        if not data:
            return None
        if data[0][0] == 0:
            return True
        return False
        
    def getCoder(this, codingjobid, setnr):
        query = 'SELECT coder_userid FROM codingjobs_sets WHERE codingjobid=%s AND setnr=%s' % \
                                                                                    (codingjobid, setnr)
        data = this.doQuery(query, colnames=0)
        if data:
            return data[0][0]
        else:
            return None
            
    def changeCoder(this, codingjobid, setnr, coderid):
        params=['@jobid=%s'%codingjobid]
        params.append('@setnr=%s'%setnr)
        params.append('@newcoderid=%s'%coderid)
        this.doQuery('exec changecodingjobsetcoder %s' % (', '.join(params)))
    
    def changeJobOwner(this, codingjobid, ownerid):
        params=['@jobid=%s'%codingjobid]
        params.append('@newownerid=%s'%ownerid)
        this.doQuery('exec changecodingjobowner %s' % (', '.join(params)))
        
    def deleteJob(this, codingjobid):
        params=['@jobid=%s'%codingjobid]
        this.doQuery('exec deletecodingjob %s' % (', '.join(params)))
        
    def deleteCodingSet(this, codingjobid, setnr):
        params=['@jobid=%s'%codingjobid]
        params.append('@setnr=%s'%setnr)
        this.doQuery('exec deletecodingjob_set %s' % (', '.join(params)))
        
    def getSelectionInfo(this, selectionid):
        query = "SELECT query, config FROM storedresults where storedresultid = %s" % selectionid
        return this.doQuery(query, colnames=0)
        
    def batchList(this, projectid, colnames=1):
        query = """SELECT batchid, batch as batchname, project, narticles as articles 
                    FROM vw_batches_counts
                    WHERE projectid=%s and batchid is not null
                    ORDER BY batchid""" % projectid
        return this.doQuery(query, colnames=colnames)
        
    def getBatchInfo(this, batchid, details=None):
        if details:
            extra = ', project' 
        else:
            extra = ''
        query = "select batchid, batch as batchname, projectid, owner%s from vw_batches_counts where batchid=%s" % (extra,batchid)
        return this.doQuery(query, colnames=1)

    """def returnUserSelect(this, currentOwner=0, multiple=0, name="ownerid"):
        html = '<select name=%s %s>' % (name, multiple and 'multiple size=10' or '')
        data = this.doQuery('select userid, fullname from users')
        for userid, fullname in data:
            if userid == currentOwner:
                html += '<option value="%s" selected>%s</option>' % (userid,fullname)
            else:
                html += '<option value="%s">%s</option>' % (userid,fullname)
        html += '</select>'
        return html"""
        
    def getIndices(this, colnames=0, done=1, started=1):
        query = """SELECT directory, indexid, name, owner_userid
                    FROM indices
                    WHERE done = %(done)s AND started = %(started)s
                    ORDER BY indexid DESC""" % locals()
        data = this.doQuery(query, colnames=colnames)
        return [ (row[0], '%s - %s' % (row[1], row[2]), row[3]) for row in data]
        
    def getUserList(this):
        return this.doQuery('SELECT userid, fullname FROM users ORDER BY fullname', colnames=0)

    def getUserInitials(this, userid):
        return this.getValue('SELECT initials FROM users WHERE userid=%i' % userid)
    
    def getValue(this, sql):
        data = this.doQuery(sql)
        if data:
            return data[0][0]
        return None

    def getColumn(this, sql, colindex=0):
        for col in this.doQuery(sql):
            yield col[colindex]

    def uploadimage(this, articleid, length, breadth, abovefold, type=None, data=None, filename=None, caption=None):
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
            p = this.doQuery("SELECT min(parnr) FROM sentences WHERE articleid=%i" % articleid)[0][0]
        except:
            p = None
        
        if p: p = int(p)
        else: p = 1 # if no sentences are present yet

        if p >= 0: newp = -1
        else: newp = p - 1

        ins = {"articleid" : articleid, "parnr" : newp, "sentnr": 1, "sentence" : "[PICTURE]"}
        sid = this.insert("sentences", ins)

        if not sid:
            raise Exception("Could not create sentence")

        if caption:
            for i, line in enumerate(sbd.split(caption)):
                if not line.strip(): continue
                ins = {"articleid" : articleid, "parnr" : newp, "sentnr": 2 + i, "sentence" : line.strip()}
                this.insert("sentences", ins, retrieveIdent=0)

        fold = abovefold and 1 or 0
        ins =  {"sentenceid" : sid, "length" :length, "breadth" : breadth,
                "abovefold" : fold, "imgdata" : data, "imgType" : type}
        this.insert("articles_images", ins, retrieveIdent=0)
        return sid

if __name__ == '__main__':
    print "Opening connection with database"
    db = anokoDB()
    #print "Trying to upload image from sys.argv[1] for article sys.argv[2] with optional caption sys.argv[3]"
    #import sys
    #caption = None
    #if len(sys.argv) > 3:
    #    caption = sys.argv[3]
    #db.uploadimage(int(sys.argv[2]), 0, 0, 0, filename=sys.argv[1], caption=caption)
    print "Reading project name"
    print db.doQuery("select top 1 * from projects")
