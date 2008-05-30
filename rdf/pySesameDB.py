
#	 pySesame is freeDB software; you can redistribute it and/or modify
#	 it under the terms of the GNU General Public License as published by
#	 the Free Software Foundation; either version 2 of the License, or
#	 (at your option) any later version.
#
#	 pySesame is distributed in the hope that it will be useful,
#	 but WITHOUT ANY WARRANTY; without even the implied warranty of
#	 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	 GNU General Public License for more details.
#
#	 A copy of the full General Public License is available at
#	 http://www.gnu.org/copyleft/gpl.html and from the Free Software
#	 Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.
#

"""
'almost' DB API compliant Sesame connector

Deliberately not compliant on these aspects
- binary(..) not implemented since Sesame has no binary type
- executeMany(..) not implemented since this is not useful for select
  queries and Sesame has not modification queries
- description returns type info for the current row as Sesame columns
  are not strongly types. If a cell on the current row is None, the
  typecode matches NONETYPE (which is not allowed by the API)

Notes:
- RDF URI type is represented as the ROWID typecode
- Each data type is mapped to a appropriate python type; URI is mapped
  to the trivial unicode subclass URI defined in this module, dates are
  mapped to mx.DateTime.DateTime objects
- Sesame has no transaction support and no modification queries
  (instead use the upload and remove methods of the httpConn attribute)
- The connection has an execute method that directly returns the data
  from sesame as a list of rows. Since sesame immediately returns all
  data from a query, there is no efficiency loss compared to using
  cursors. In fact, Cursor.execute calls this method to obtain its
  data set and cursors are only provided for API compliance
- Optional DB API cursor attribute rownumber and connection and methods
  scroll and __iter__ are implemented (although iter(Connection.execute)
  also works and makes more sense)
"""

import pySesame
import mx.DateTime
import mx.DateTime.ISO
import types

from xml.sax.handler import ContentHandler


BINARY, NONETYPE, STRING, NUMBER, DATETIME, ROWID = range(-1,5)

xsd_typehandlers = {
    'http://www.w3.org/2001/XMLSchema#date' : mx.DateTime.ISO.ParseDate,
    'http://www.w3.org/2001/XMLSchema#dateTime' : mx.DateTime.ISO.ParseDateTime,
    'http://www.w3.org/2001/XMLSchema#time' : mx.DateTime.ISO.ParseTime,
    'http://www.w3.org/2001/XMLSchema#date' : mx.DateTime.ISO.ParseDate,
    'http://www.w3.org/2001/XMLSchema#int' : int,
    'http://www.w3.org/2001/XMLSchema#long' : long,
    'http://www.w3.org/2001/XMLSchema#string' : unicode,
    'http://www.w3.org/2001/XMLSchema#decimal' : float, # no fixed precision decimal in python?
    'http://www.w3.org/2001/XMLSchema#double' : float,
    'http://www.w3.org/2001/XMLSchema#float' : float,
    'http://www.w3.org/2001/XMLSchema#boolean' : (lambda x:x.lower() in ('true',1)),
    }

class URI(unicode):
    """Subclass of unicode to distinguish normal strings from uri's"""
    # [WvA] Yuck!
    def __init__(self, *args, **kargs):
        super(URI, self).__init__(*args, **kargs)
    def __repr__(self):
        return "uri'%s'" % self

_URI_TYPE = type(URI())
def isURI(obj):
    return type(obj) == _URI_TYPE 
                
apilevel = "2.0 Incomplete"
threadsafety = 3
paramstyle = 'pyformat'


class SesameDBConnection(object):
    """DB API Connection class"""

    def __init__(self, dsn=None, user=None, password=None, database=None,
                 host=None, port=8080, sesamedir="sesame", queryLanguage='SeRQL',
                 namespaces=None, repository=None, **kargs):
        """
        DB API connect method
        
        This method will create a SesameDBConnection object to the specified DSN, which
        should point to a valid sesame URL. If DSN is not given, this will construct
        a DSN of form 'http://HOST:PORT/SESAMEDIR'.
        
        If user and password are given, this method will subsequently call the login method
        on the connection object. If repository or namepsaces are given, this method will set
        the relevant attribute of the connection to the specified value. Database is an alias
        for repository for DB API suggested fingerprint compliance.
        
        Any unexpected keyword arguments will be passed to the SesameHTTPConnection constructor
        """
        if not dsn:
            if not host and port and sesamedir:
                raise Error("Need to specify eiter DSN or HOST!")
            dsn = 'http://%s:%s/%s/' % (host, port, sesamedir)
            
        self.httpConn = pySesame.SesameConnection(dsn, **kargs)

        if user:
            self.httpConn.login(user, password)

        self.queryLanguage=queryLanguage
        self.ns=namespaces
        self.repository=repository or database

        
    def close(self):
        self.httpConn.close()

    def commit(self):
        pass

    def cursor(self):
        return Cursor(self)

    def execute(self, query, returnHeader = 0, params=None):
        """
        Execute a serql-select query and return the resulting table.
        If returnHeader is true, returns a (data, header) pair.
        """
        if self.ns:
            query += '\n\n%s' % self.ns.NS()

        if params:
            query = query % params

        handler = SelectQueryHandler2()
        try:
            data, header = self.httpConn.doQuery(query, self.repository,
                                                 self.queryLanguage, handler)
        except Exception, e:
            raise Exception("Error on executing SeRQL:\n%s\nException: %s" % (query, e))
        
        if returnHeader:
            return (data, header)
        else:
            return data

    def construct(self, query, params= None):
        """
        Execute a serql-select query and return the resulting table.
        If returnHeader is true, returns a (data, header) pair.
        """
        if self.ns:
            query += '\n\n%s' % self.ns.NS()

        if params:
            query = query % params

        try:
            result = self.httpConn.graphQuery(self.repository,
                                                 self.queryLanguage, query)
        except Exception, e:
            raise Exception("Error on executing SeRQL:\n%s\nException: %s" % (query, e))
        
        return result

class Cursor(object):

    def __init__(self, connection):
        self.connection = connection
        self.data = None
        self.header = None
        self.open = True
        self.rownumber = None
        self.arraysize = 10

    def getDescription(self):
        """
        Since data types in SeRQL are dynamic, will return the description
        for the row that will be fetched next
        """
        return list((h, self.typeOf(i), None, None, None, None, None) for i, h in enumerate(self.header))

    def typeOf(self, colno):
        """
        Returns the typecode of column #colno
        
        Since data types in SeRQL are dynamic, will return the description
        for the row that will be fetched next
        """
        if self.rownumber is None: raise Error("No results available")

        rowno = self.rownumber
        if self.rownumber >= len(self.data): rowno = 0
        cell = type(self.data[rowno][colno])
        if cell is None: return None
        
        t = type(self.data[rowno][colno])
        if t==types.UnicodeType: return STRING
        if t in (types.IntType, types.FloatType): return NUMERIC
        if t in (mx.DateTime.DateTimeType, mx.DateTime.DateTimeDeltaType): return DATETIME
        if t is URI: return ROWID
        raise Error("Unrecognized type %s" % t)    
        
    def execute(self, query, params=None):
        self.data, self.header = self.connection.execute(query, returnHeader=1, params=params)
        self.rownumber = 0

    def fetchOne(self):
        if self.rownumber is None:
            raise Error("No results available")
        if self.rownumber >= len(self.data):
            return None
        data = self.data[self.rownumber]
        self.rownumber += 1
        return data
    
    def fetchMany(self, size=None):
        if size is None: size = self.arraysize
        if self.rownumber is None:
            raise Error("No results available")

        data = self.data[self.rownumber:self.rownumber+size]
        self.rownumber += size
        return data

    def fetchAll(self):
        data = self.data[self.rownumber:]
        self.rownumber = len(self.data)
        return data
    
    def setinputsizes(*args, **kargs):
        pass
    def setoutputsize(*args, **kargs):
        pass
    
    def getRowCount(self):
        if not self.open: raise Error("Cursor has been closed")
        if self.data:
            return len(self.data)
        else:
            return -1

    def close(self):
        del(self.data)
        del(self.connection)
        self.open = False

    def __iter__(self):
        return iter(self.fetchAll())
    def scroll(self, value, mode='relative'):
        if mode=='relative':
            value = self.rownumber + value
        self.rownumber = value
        
    description=property(fget=getDescription, doc="Read-only description attribute for DB API compliance")
    rowcount   =property(fget=getRowCount, doc="Read-only description attribute for DB API compliance")
    
# Some methods for DB API Compliance
connect = SesameDBConnection
import time
def DateFromTicks(ticks):
    return Date(*time.localtime(ticks)[:3])
def TimeFromTicks(ticks):
    return Time(*time.localtime(ticks)[3:6])
def TimestampFromTicks(ticks):
    return Timestamp(*time.localtime(ticks)[:6])
from mx.DateTime import Date, Time
Timestamp = mx.DateTime.DateTime

class SelectQueryHandler2(ContentHandler):
    """
    After a succesful parse
      .columns is a list of columns headers and
      .data is a list of lists of cell values
    """
    # [WvA] New version of SelectQueryHandler
    #       returns lists of lists of values, which
    #       have the 'correct' type.
    def __init__ (self):
        self.columns = []
        self.data = []
        self.results  = self.data, self.columns
        
        # XML state:
        self._tuple = None
        self._chars = None
        self._currentElement = None
        self._currentLiteralType = None
        
    def startElement(self, name, attrs):
        if name == 'tuple':
            self._tuple = []
            self.inTuple = 1

        self._currentLiteralType = attrs.get('datatype', None)
        self._chars = ""
        self._currentElement = name

    def characters(self, ch):
        self._chars += ch

    def endElement(self, name):
        if name == 'tuple':
            self.data.append(self._tuple)
            self._tuple = None
            self._inTuple = 0
        elif name == 'columnName':
            self.columns.append(self._chars)
        elif self._tuple is not None:
            datatype = self._currentLiteralType
            if name=='uri':
                val = URI(self._chars)
            elif datatype:
                if datatype in xsd_typehandlers:
                    val = xsd_typehandlers[datatype](self._chars)
                else:
                    raise InterfaceError("XSD type %s not handled, add to xsd_typehandlers" % datatype)
            else:
                val = self._chars
            self._tuple.append(val)

# Exception hierarchy prescripbed by DB API
import exceptions

class Error(exceptions.StandardError):
    pass
    
class Warning(exceptions.StandardError):
    pass
    
class InterfaceError(Error):
    pass

class DatabaseError(Error):
    pass

class InternalError(DatabaseError):
    pass

class OperationalError(DatabaseError):
    pass

class ProgrammingError(DatabaseError):
    pass

class IntegrityError(DatabaseError):
    pass

class DataError(DatabaseError):
    pass

class NotSupportedError(DatabaseError):
    pass

class SesameServerError(DatabaseError):
    pass
        

                                        
