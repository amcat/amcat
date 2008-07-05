"""
Module to connect with Sesame 2 servers over HTTP
Python DB API 2.0 compliant (see the DB API specs
at http://www.python.org/dev/peps/pep-0249/)

Limitations:
- only supports SeRQL table queries and extracting all data

Download at http://www.content-analysis.org/misc/pySesame2.py

(C) 2007 Wouter van Atteveldt
All rights reserved.  Redistribution and use in source and binary
forms, with or without modification, are permitted provided that the
following conditions are met:
* Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.
THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS''
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import exceptions
import urllib2, urllib,re
import datetime, types
import decimal

MIME = {"rdf" : "application/rdf+xml",
        "n3" : "text/rdf+n3"}


class _TableHandler(object):
    """Iterable parser for the sesame binary table format
    http://www.openrdf.org/doc/sesame/api/org/openrdf/sesame/query/BinaryTableResultConstants.html
    """

    def __init__(self, stream):
        self.stream = stream
        if self.stream.read(4) <> 'BRTR': raise ParseError("First 4 bytes in table result should be BRTR")
        self.readint() # protocol version
        self.ncols = self.readint()
        self.columns = tuple(self.readstr() for x in range(self.ncols))
        self.cndict = dict(zip(self.columns, range(len(self.columns))))
        self.ns = {}
        
    def readint(self):
        s = self.stream.read(4)
        if len(s) <> 4: raise ParseError
        return ord(s[0]) * 2**24 + ord(s[1]) * 2**16 + ord(s[2]) * 2**8  + ord(s[3])
    
    def readstr(self):
        l = self.readint()
        return self.stream.read(l).decode("utf-8")

    def __iter__(self):
        return self

    def next(self):
        vals = []
        for i in range(self.ncols):
            try:
                val = self.getvalue()
            except EOF_PSEUDO_ERROR:
                raise StopIteration()
            if val == _REPEAT:
                vals.append(self.oldvals[i])
            else:
                vals.append(val)
        self.oldvals = MappingTuple(self.cndict, vals)
        return self.oldvals

    #print `stream.read()`
    #return


    def getvalue(self):
        currentliteral = None
        while True:
            rtype = ord(self.stream.read(1))
            if rtype == 0: #NULL
                return None
            elif rtype == 1: #REPEAT
                return _REPEAT
            elif rtype == 2: #NAMESPACE 
                id = self.readint()
                url = self.readstr()
                self.ns[id] = url
            elif rtype == 3: # QNAME
                nsid = self.readint()
                localname = self.readstr()
                uri = self.ns[nsid] + localname
                if currentliteral:
                    l = _literal(currentliteral, uri)
                    currentliteral = None
                    return l
                else:
                    return self.ns[nsid] + localname
            elif rtype == 6: # PLAIN LITERAL
                return self.readstr()
            elif rtype == 8: # DATATYPE LITERAL
                currentliteral = self.readstr()
            elif rtype == 127: # EOF
                raise EOF_PSEUDO_ERROR
                return None
            else:
                raise ParseError("Undefined record type: %s" % rtype)


class Output:
    """Defines a 'smart constant' for output types

    Each type should be an instance of Output, defining a String-valued
    accept (for the HTTP header), and a one-argument function handle that
    will be called with the stream yielded by the HTTP request

    Builtin constants:
    NONE : no header and no handler, will return the stream itself
    RDFXML: rdfxml header, will return the string containing the RDF/XML
    TABLE: binary table header, will return an iterable of MappingTuple
    """
    
    def __init__(self, accept = None, handle = None):
        self.accept = accept
        self.handle = handle

    NONE, TABLE, RDFXML = None, None, None # handlers are defined below

class GETType:
    """Defines an enumeration for the HTTP request verb"""
    GET, POST, PUT, DELETE = "GET", "POST", "PUT", "DELETE"

Output.NONE = Output()
Output.RDFXML = Output('application/rdf+xml', lambda x : x.read())
Output.TABLE = Output('application/x-binary-rdf-results-table', _TableHandler)

class _Constants:
    URL_PROTOCOL = "protocol"
    REPOSITORIES = "repositories"
    NAMESPACES = "namespaces"
    QUERY = "" # query is server/repositories/<repo>?query=
    STATEMENTS = "statements"

    DEFAULT_SERVER = "http://localhost:8088/openrdf-sesame"
    DEFAULT_REPO = "anoko-test"
    DEFAULT_REPO = "anoko"

    
    OK_VERSION = '4'

class Connection(object):
    def __init__(self, uri=_Constants.DEFAULT_SERVER, user=None,
                 password=None, database=_Constants.DEFAULT_REPO):
        if not uri.endswith("/"): uri += "/"
        self.uri = uri
        self.repo = None
        self.namespaces = None
        self._checkServerProtocol()
        if database:
            self.use(database)

    # DB-API public interface

    def close(self): 
        """Close the connection
    
        Close the connection now (rather than whenever __del__ is
        called).  The connection will be unusable from this point
        forward; an InvalidStateError will be raised if any operation
        is attempted with the connection. The same applies to all
        cursor objects trying to use the connection.
        """
        self._release()
        self.uri = None
        del(self.repo)
        del(self.namespaces)
    
    def commit(self):
        """Does nothing."""
        pass
    
    def rollback(self): 
        """Does nothing."""
        pass

    def cursor(self):
        """Return a new Cursor Object using the connection"""
        self._checkHasDB()
        return Cursor(self)
    
    # Sesame2-specific public interface
    def use(self, repository):
        """Switch to this repository (database)"""
        self._checkNotClosed()
        if (repository == self.repo): return
        self._release()
        self.repo = repository
        if self.repo: self._getNamespaces()

    def repositories(self):
        self._checkNotClosed()
        return self._getTable(_Constants.REPOSITORIES)

    def execute(self, query, output = Output.TABLE):
        """Execute the given SeRQL. Returns an iterable of MappingTuple (default)"""
        self._checkHasDB()
        return self._execute(query, self.repo, self.namespaces, output = output)

    def extract(self, output = Output.RDFXML):
        """Extract all data as RDF/XML (default)"""
        self._checkHasDB()
        return self._get(_Constants.STATEMENTS, repo=self.repo, output = output)

    def add(self, rdf, contenttype="application/rdf+xml"):
        """Add the given data (assumes RDF/XML)"""
        self._checkHasDB()
        self._get(_Constants.STATEMENTS, repo=self.repo, output=Output.NONE, params = rdf, gettype=GETType.POST, contenttype=contenttype)

    def delete(self):
        """Delete all data in the repository"""
        self._checkHasDB()
        self._get(_Constants.STATEMENTS, repo=self.repo, output=Output.NONE, gettype=GETType.DELETE)

    def nsexpand(self, uri, ns = None):
        """Collapses (expands) the URI using the given namespace dict
        or the namespaces in the current Repository"""
        if not ns: ns = self.namespaces
        for k, v in ns.items():
            if uri.startswith(k+":"):
                return v+uri[len(k)+1:]
        return uri

    def nscollapse(self, uri, ns = None):
        """Collapses (abbreviates) the URI using the given namespace dict
        or the namespaces in the current Repository"""
        if not type(uri) in types.StringTypes: return uri
        if not ns: ns = self.namespaces
        for k, v in ns.items():
            if uri.startswith(v):
                return k+":"+uri[len(v):]
        return uri

    # Private methods

    def _execute(self, query, repo, ns, output = Output.TABLE):
        nsstr = '\nUSING NAMESPACE\n%s\n' % ',\n'.join("   %s = <%s>" % kv for kv in ns.items())
        if 'USING NAMESPACE' in query:
            query = query.replace('USING NAMESPACE', nsstr)
        else:
            query += nsstr

        params = {'query': query, 'queryLn' : 'serql'}
        try:
            return self._get(_Constants.QUERY, params=params, repo=repo, output = output, gettype=GETType.POST)
        except ConnectionError, e:
            raise ProgrammingError("Error on executing:\n%s\n%s" % (query, e))

    def _release(self):
        self.namespaces = None

    def _getNamespaces(self):
        self.namespaces = {}
        for pref, uri in self._getTable(_Constants.NAMESPACES, repo = self.repo):
            self.namespaces[pref] = uri
        

    def _checkNotClosed(self):
        if not self.uri:
            raise InvalidStateError("The pySesame2 connection has been closed")

    def _checkHasDB(self):
        self._checkNotClosed()
        if not self.repo:
            raise InvalidStateError("No repository (database) has been selected yet")

    def _checkServerProtocol(self):
        pversion = self._get(_Constants.URL_PROTOCOL, output=Output.NONE).read()
        if pversion.strip() <> _Constants.OK_VERSION:
            raise ConnectionError("Server at %s reports protocol version '%s', %s was required" %
                                  (self.uri, pversion, _Constants.OK_VERSION))

    def _get(self, file, params = {}, accept = None, repo = None, output = Output.RDFXML, gettype = GETType.GET, contenttype=None):

        #build uri
        if repo:
            if file: file = "/%s" % file
            file = "repositories/%s%s" % (repo, file)
        query, data = "", None
        if params:
            if gettype == GETType.POST:
                if type(params) == str:
                    data = params
                else:
                    data = urllib.urlencode(params)
            elif gettype == GETType.GET:
                query = "?"+urllib.urlencode(params)
                                
        uri = "%s%s%s" % (self.uri, file, query)

        #build request
        request = ExtendedRequest(uri)
        request.set_method(gettype)
        if data:
            request.add_data(data)
        if output.accept:request.add_header('Accept', output.accept)
        if contenttype:request.add_header('Content-Type', contenttype)

        #execute
        try:
            result = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            if '404' in str(e):
                raise ConnectionError("Server does not exist or invalid request: '%s':\n%s" % (uri ,e))
            elif '204' in str(e):
                return None
            raise ConnectionError("Server gives an error for uri '%s' (POST DATA:%s):\n%s" % (uri ,request.get_data(), e))
        if output.handle:
            return output.handle(result)
        else:
            return result

    def _getTable(self, *args, **kargs):
        kargs['output'] = Output.TABLE
        return self._get(*args, **kargs)

    def _getRDF(self, *args, **kargs):
        kargs['output'] = Output.RDFXML
        return self._get(*args, **kargs)
    
class Cursor(object):
    """
    These objects represent a database cursor, which is used to manage
    the context of a fetch operation. Cursors created from the same
    connection are not isolated, i.e., any changes done to the
    database by a cursor are immediately visible by the other
    cursors.
    """

    def __init__(self, conn):
        self.conn = conn
        self.repo = conn.repo
        self.ns = conn.namespaces

        self._results = None
        
        self.description = None # DB API
        self.rowcount = None # DB API
        self.arraysize = 10 # DB API
        
    # DB API public methods

    #def callproc(self, procname, parameters = None)
    #def nextset(self)
    #not implemented, let python generate an AttributeError

    def close(self):
        self.conn = None
        del(self.repo)
        del(self.ns)
    
    def execute(self, operation, parameters = None):
        """Executes a database query"""
        self._checkNotClosed()
        if parameters: operation = operation % parameters
        self._results = iter(self.conn._execute(operation, self.repo, self.ns))

    def executemany(self, operation, seq_of_parameters):
        """Prepare a database operation (query or command) and then
        execute it against all parameter sequences or mappings
        found in the sequence seq_of_parameters.
        """ 
        for params in seq_of_parameters:
            self.execute(params)

    def fetchone(self):
        """Fetch a single row

        Fetch the next row of a query result set, returning a
        single TupleMapping, or None when no more data is
        available.
        """
        
        self._checkHasResults()
        try:
            return self._results.next()
        except StopIteration:
            self._results = None
            return None

    def fetchmany(self, size = None):
        """ Fetch a set of rows

        Fetch the next set of rows of a query result, returning a
        sequence of sequences (e.g. a list of tuples). An empty
        sequence is returned when no more rows are available.
        """
        
        result = []
        for i in range(size or self.arraysize):
            res = self.fetchone()
            if res is None: break
            result.append(res)
        return result

    def fetchall(self):
        """Fetch all (remaining) rows

        Fetch all (remaining) rows of a query result, returning them
        as a sequence of sequences (e.g. a list of tuples).  Note that
        the cursor's arraysize attribute can affect the performance of
        this operation.
        """
        self._checkHasResults()
        return tuple(self._results)
    
    def setinputsizes(self, sizes):
        """Does nothing."""
        pass
    def setoutputsize(self, size, column=None):
        """Does nothing."""
        pass

    def __iter__(self):
        """Returns an iterator over the (remaining) results"""
        self._checkHasResults()
        return self._results

    # private methods

    def _checkNotClosed(self):
        if not self.conn:
            raise InvalidStateError("The pySesame2 cursor has been closed")
        self.conn._checkNotClosed()
    def _checkHasResults(self):
        self._checkNotClosed()
        if not self._results:
            raise InvalidStateError("No resultset is available")
    

class MappingTuple(tuple):
    """A tuple that functions as a limited mapping (dict)

    Initialized by giving a tuple and a map of column names->indexes.
    Functions as a tuple but allows for indexing using the
    names defined in the column name map. Also provides keys() and items()
    as expected, and asDict() returns a copy of this object as a real
    dictionary.

    """
    def __new__(cls, cndict, *args, **kargs):
        return tuple.__new__(cls, *args, **kargs)
    def __init__(self, cndict, *args, **kargs):
        tuple.__init__(*args, **kargs)
        self.cndict = cndict
    def __getitem__(self, index):
        if type(index) <> int:
            index = self.cndict[index]
        return tuple.__getitem__(self, index)
    def keys(self):
        return self.cndict.values()
    def items(self):
        return [(i[0], self[i[1]]) for i in self.cndict.items()]
    def asDict(self):
        return dict(self.items())

def debug(lvl, str):
    import sys
    print >>sys.stderr, "%s : %s" % (lvl, str)

def _readdate(s):
    ymd = None
    m = re.search("(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        ymd = [int(x) for x in m.groups()]
    if ymd:
        return datetime.date(*ymd)
    debug(1, "Could not interpret date string %r" % s)
    return None

_LiteralTypes = {
    "http://www.w3.org/2001/XMLSchema#boolean" : lambda x : x.lower().strip() == 'true',
    "http://www.w3.org/2001/XMLSchema#string": unicode,
    "http://www.w3.org/2001/XMLSchema#date": _readdate,
    "http://www.w3.org/2001/XMLSchema#decimal": decimal.Decimal,
    }
# how to make a guaranteed unique object??
class _REPEAT: pass 

def _literal(label, typeurl):
    #print "l", `label`
    #print "u", `typeurl`
    if typeurl not in _LiteralTypes:
        raise ParseError("Unknown literal type: %s / %s" % (typeurl, label))
    return _LiteralTypes[typeurl](label)
        


# Exception hierarchy as required by Python DB API

class Error(exceptions.StandardError):pass
class InterfaceError(Error):pass
class ParseError(Error):pass
class NotImplementedError(InterfaceError,exceptions.NotImplementedError):pass
class OperationalError(Error):pass
class InvalidStateError(Error):pass
class ConnectionError(OperationalError):pass
class ProgrammingError(Error): pass

class EOF_PSEUDO_ERROR(Exception): pass

# Global variables as defined by Python DB API
apilevel = "2.0"
threadsafety = 1
paramstyle = 'pyformat'

class ExtendedRequest(urllib2.Request):
    """Extension of urllib2.Request to allow PUT and DELETE

    For some reason, urllib2.Request does not have a
    set_method method, and simply does a POST or GET depending
    on the contens of get_data()

    This class extends Request with a set_method call. If this
    is called with a 'true' value, it will use that method.
    Otherwise, it behaves as urllib2.Request.
    """
    
    def __init__(self, *args, **kargs):
        urllib2.Request.__init__(self,*args, **kargs)
        self._pref_method = None

    def set_method(self, method):
        self._pref_method = method

    def get_method(self):
        if self._pref_method:
            return self._pref_method
        else:
            return urllib2.Request.get_method(self)


def connect(*args, **kargs):
    """Connect to a Sesame2 server over HTTP
    Parameters:

    uri: the full uri of the server (http://example.org/openrdf-sesame)
    user and password (both optional): the credentials to log in with (ignored)
    database: the repository to select on the server
    """
    return Connection(*args, **kargs)
    
if __name__ == '__main__':
    import sys
    def printusage():
        print """Usage: pySesame2.py [-Sserver] [-Rrepo] COMMAND [ARGS]
        Executes the COMMAND against the given server/repo (or the default)

        COMMAND:
        QUERY   ARGS should be a serql query to execute
        EXTRACT extracts all data as RDF/XML to <stdout>
        UPLOAD  upload the data from <stdin> to the server
        DELETE  clear the repository
        """
        sys.exit(1)
    if len(sys.argv) == 1:
        printusage()

    server, repo = _Constants.DEFAULT_SERVER, _Constants.DEFAULT_REPO
    args = sys.argv[1:]
    print args
    if args[0][:2] == '-S':
        server = args[0][2:]
        del(args[0])
    if args[0][:2] == '-R':
        repo = args[0][2:]
        del(args[0])
    if args[0] == 'N3':
        N3 = True
        del(args[0])
    else:
        N3 = False
    cmd = args[0]
    del(args[0])

    print >>sys.stderr, "Connecting to %s/%s" % (server, repo)
    db = connect(server, database = repo)
    if cmd == "QUERY" and args:
        print >>sys.stderr, "Executing query"
        for row in db.execute(" ".join(args)):
            print "\t".join(str(x) for x in row)
    elif cmd == "EXTRACT":
        print >>sys.stderr, "Extracting all data"
        rdf = db.extract()
        print >>sys.stderr, "Extracted %i bytes" % len(rdf)
        print rdf
    elif cmd == "UPLOAD":
        rdf = sys.stdin.read()
        if N3:
            print >>sys.stderr, "Using N3 format"
            ctype= MIME['n3']
        else:
            ctype = MIME['rdf']
        print >>sys.stderr, "Adding %i bytes" % len(rdf)
        db.add(rdf, contenttype=ctype)
    elif cmd == "CLEAR":
        import time
        print >>sys.stderr, "Clearing repository in 3 seconds"
        for i in (2,1,"Clearing..."):
            time.sleep(1)
            print >>sys.stderr, i
        db.delete()
    else:
        printusage()

