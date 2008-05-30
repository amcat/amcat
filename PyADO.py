#PyADO V0.1
# Copyright (c) Shayan Raghavjee, David Fraser of St James Software 2002

# Still to implement:
# --------------------------------------------------------------------
# Module              - paramstyle not yet determined
# Errors & Exceptions - still need to get done
# Connection Objects  - commit & rollback
# Cursor Objects      - rowcount, callproc, setinputsizes, setoutputsize
# Type Objects        - still need to get done (use mxDateTime)
# --------------------------------------------------------------------
# 
# PyADO, an ADO wrapper for the Python Database API
# Home Page: http://pyado.sourceforge.net/
# Released under the Python license, PSF version.
# For Pythond API Reference, see http://www.python.org/topics/database/DatabaseAPI-2.0.html

import pythoncom
import win32com.client

# This section contains the enum definitions for ADO type constants
# taken from VC++ ADOINT.H

# array/vector/byref types
# couldn't find this in adoint.h so
# these are currently set to 0 which means they'll be ignored
adArray = 0
adByRef = 0
adVector = 0

# DataTypeEnum
# actual standard types
adEmpty = 0
adTinyInt = 16
adSmallInt = 2
adInteger = 3
adBigInt = 20
adUnsignedTinyInt = 17
adUnsignedSmallInt = 18
adUnsignedInt = 19
adUnsignedBigInt = 21
adSingle = 4
adDouble = 5
adCurrency = 6
adDecimal = 14
adNumeric = 131
adBoolean = 11
adError = 10
adUserDefined = 132
adVariant = 12
adIDispatch = 9
adIUnknown = 13
adGUID = 72
adDate = 7
adDBDate = 133
adDBTime = 134
adDBTimeStamp = 135
adBSTR = 8
adChar = 129
adVarChar = 200
adLongVarChar = 201
adWChar = 130
adVarWChar = 202
adLongVarWChar = 203
adBinary = 128
adVarBinary = 204
adLongVarBinary = 205
adChapter = 136
adFileTime = 64
adDBFileTime = 137
adPropVariant = 138
adVarNumeric = 139

# FieldAttributesEnum
# at the moment we just use adFldMayBeNull
adFldUnspecified = -1
adFldMayDefer = 0x2
adFldUpdatable = 0x4
adFldUnknownUpdatable = 0x8
adFldFixed = 0x10
adFldIsNullable = 0x20
adFldMayBeNull = 0x40
adFldLong = 0x80
adFldRowID = 0x100
adFldRowVersion = 0x200
adFldCacheDeferred = 0x1000
adFldNegativeScale = 0x4000
adFldKeyColumn = 0x8000


def connect(dsn,user=None,password=None,host=None,database=None,provider=None):
    """Constructor for creating a connection to the database. Returns a Connection Object.
    
    It takes a number of parameters which are database dependent:
    dsn        Data source name as string
    user       User name as string (optional)
    password   Password as string (optional)
    host       Hostname (optional)
    database   Database name (optional)
    provider   OLE DB Provider name  (optional paramater, but required to work)"""
    
    NewConn = Connection()
    NewConn.connect(dsn,user=user,password=password,host=host,database=database,provider=provider)
    return NewConn

# String constant stating the supported DB API level, currently 2.0
apilevel = '2.0'

# Integer constant stating the level of thread safety the interface supports.
threadsafety = 2  # Threads may share the module and connections. (guess)

# String constant stating the type of parameter marker formatting expected by the interface.
# since this is different for different providers, we need to work it out
paramstyle = 'pyformat'  # Python extended format codes, e.g. '...WHERE name=%(name)s'

# type objects. we can make these more complex later if neccessary
STRING = 1
BINARY = 2
NUMBER = 3
DATETIME = 4
ROWID = 5
UNKNOWN = 0 # we really shouldn't have this

class Connection:
    """PyADO Connection, follows DatabaseAPI-2.0
    
    __init__()
        Initialises the internal connection object using win32com
    connect(dsn,user,password,host,database,provider)
        open the connection. this is called from the connect function outside this class
      cursor()
        Return a new Cursor Object using the connection.
      close()
        Close the connection now (rather than whenever __del__ is called).
    commit() [not implemented]
         Commit any pending transaction to the database.
    rollback() [optional] [not implemented]
        Does a rollback."""

    def __init__(self):
        """Initialises the internal connection object using win32com"""
        self.Conn = win32com.client.Dispatch("ADODB.Connection")
        
    def connect(self, dsn,user=None,password=None,host=None,database=None,provider=None):
        """open the connection. this is called from the connect function outside this class"""
        # currently don't do anything with dsn

        # check it's not already open
        if self.Conn.State == 1: self.Conn.Close()

          # Make connection with the given parameters. provider should be required
        if (provider <> None): self.Conn.Provider = str(provider)
        if (host <> None):
            # using SQL Server-style with Data Source=host and Initial Catalog=database
            self.Conn.Properties("Data Source").Value = str(host)
            if (database <> None): self.Conn.Properties("Initial Catalog").Value =  str(database)
        else:
            # using Oracle-style with no host, Data Source=database
            if (database <> None): self.Conn.Properties("Data Source").Value = str(database)
        if (user <> None): self.Conn.Properties("User ID").Value = str(user)
        if (password <> None): self.Conn.Properties("Password").Value = str(password)

        # open the database (pass database, username and password again)
        if (host <> None):
            # using SQL Server-style with Data Source=host and Initial Catalog=database
            self.Conn.Open(host,user,password)
        else:
            # using Oracle-style with no host, Data Source=database
            self.Conn.Open(database,user,password)

        # check whether it was Connected
        isConnected = (self.Conn.State == 1)
        # return whether this succeeded
        return isConnected
      
    def cursor(self):
        """Return a new Cursor Object using the connection."""
        return Cursor(self.Conn)
          
    def close(self):
        """Close the connection now (rather than whenever __del__ is called).
        The connection will be unusable from this point forward;
        an Error (or subclass) exception will be raised
        if any operation is attempted with the connection.
        The same applies to all cursor objects trying to use the connection."""
        
        self.Conn.Close()
      
class Cursor:
    """PyADO cursor, which is used to manage the context of a fetch operation (DatabaseAPI-2.0)

    __init__(self, Conn)                constructor
    description                         sequence of column descriptions
    rowcount                            number of rows produced/affected by last executeXXX    [not implemented]
    callproc(procname[,parameters])     Call a stored database procedure with the given name   [optional] [not implemented]
    close()                             Close the cursor now (rather than whenever __del__ is called).
    execute(operation[,parameters])     Prepare and execute a database operation (query or command). [parameters not implemented]
    executemany(operation,seq_of_parameters) Execute multiple operations                      [optional]
    fetchone()                          Fetch next row of a query result set, return a single sequence
    fetchmany([size=cursor.arraysize])  Fetch the next set of rows of a query result, returning sequence of sequences
    fetchall()                          Fetch all remaining rows of a query result, returning sequence of sequences
    nextset()                           Skip to next result set                                [optional]
    arraysize                           number of rows to fetch with fetchmany. default 1
    setinputsizes(sizes)                used before a executeXXX() to predefine memory areas   [not implemented]
    setoutputsize(size[,column])        used before executeXXX() to set column buffer size     [not implemented]
    """
    
    def __init__(self, Conn):
        """Initialises the internal Recordset object from the Connection using win32com"""
        self.arraysize = 1
        self.PassConn = Conn
        self.rs = None
        self.Fields = None
        self.rsList = []
        self.rsListPos = 0
        self.description = []
        
    def execute(self, operation, parameters=None):
        """Prepare and execute a database operation (query or command).
        Parameters may be provided as sequence or mapping
        and will be bound to variables in the operation."""
        
        self.rs = win32com.client.Dispatch("ADODB.Recordset")
        self.rsList = [self.rs]
        self.rsListPos = 0
        if parameters is None:
            Query = operation
        else:
            Query = operation % parameters
        self.rs.Open(operation, ActiveConnection = self.PassConn)
        # cache the fields. this must be done before describefields
        self.Fields = [self.rs.Fields.Item(col) for col in range(self.rs.Fields.Count)] 
        # now describe the results
        self.description = self.describefields()

    def describefields(self):
        """Describes all the fields in the rowset.
        Returns a value which is assigned to self.description in execute"""
        description = []
        for col in range(len(self.Fields)):
            field = self.Fields[col]
            name = field.Name
            fieldtype = field.Type
            # options are STRING BINARY NUMBER DATETIME ROWID
            # we need to get rid of UNKNOWNs
            # the comments are from the ADO docs
            if fieldtype & adArray: # don't know what to do with arrays.
                # Joined in a logical OR together with another type to indicate
                # that the data is a safe-array of that type (DBTYPE_ARRAY).
                fieldtype = fieldtype & (~adArray)
            if fieldtype & adByRef: # get rid of this
                # Joined in a logical OR together with another type to indicate
                # that the data is a pointer to data of the other type (DBTYPE_BYREF).
                fieldtype = fieldtype & (~adByRef)
            if fieldtype == adVector: # don't know what to do with arrays.
                # Joined in a logical OR together with another type to indicate
                # that the data is a DBVECTOR structure, as defined by OLE DB,
                # that contains a count of elements
                # and a pointer to data of the other type (DBTYPE_VECTOR).
                fieldtype = fieldtype & (~adVector) 


            type_code = UNKNOWN
            if fieldtype == adBigInt: type_code = NUMBER
            # An 8-byte signed integer (DBTYPE_I8).
            elif fieldtype == adBinary: type_code = BINARY
            # A binary value (DBTYPE_BYTES).
            elif fieldtype == adBoolean: type_code = NUMBER 
            # A Boolean value (DBTYPE_BOOL).
            elif fieldtype == adBSTR: type_code = STRING 
            # A null-terminated character string (Unicode) (DBTYPE_BSTR).
            elif fieldtype == adChar: type_code = STRING 
            # A String value (DBTYPE_STR).
            elif fieldtype == adCurrency: type_code = NUMBER 
            # A currency value (DBTYPE_CY). 
            # Currency is a fixed-point number with four digits to the right of the decimal point. 
            # It is stored in an 8-byte signed integer scaled by 10,000.
            elif fieldtype == adDate: type_code = DATETIME 
            # A Date value (DBTYPE_DATE). 
            # A date is stored as a Double, the whole part of which 
            # is the number of days since December 30, 1899, 
            # and the fractional part of which is the fraction of a day.
            elif fieldtype == adDBDate: type_code = DATETIME
            # A date value (yyyymmdd) (DBTYPE_DBDATE).
            elif fieldtype == adDBTime: type_code = DATETIME
            # A time value (hhmmss) (DBTYPE_DBTIME).
            elif fieldtype == adDBTimeStamp: type_code = DATETIME
            # A date-time stamp (yyyymmddhhmmss plus a fraction in billionths) (DBTYPE_DBTIMESTAMP).
            elif fieldtype == adDecimal: type_code = NUMBER
            # An exact numeric value with a fixed precision and scale (DBTYPE_DECIMAL).
            elif fieldtype == adDouble: type_code = NUMBER
            # A double-precision floating point value (DBTYPE_R8).
            elif fieldtype == adEmpty: type_code = UNKNOWN # I HAVE NO IDEA
            # No value was specified (DBTYPE_EMPTY).
            elif fieldtype == adError: type_code = UNKNOWN # I HAVE NO IDEA
            # A 32-bit error code (DBTYPE_ERROR).
            elif fieldtype == adGUID: type_code = BINARY # THINK ABOUT THIS
            # A globally unique identifier (GUID) (DBTYPE_GUID).
            elif fieldtype == adIDispatch: type_code = BINARY # THINK ABOUT THIS
            # A pointer to an IDispatch interface on an OLE object (DBTYPE_IDISPATCH).
            elif fieldtype == adInteger: type_code = NUMBER
            # A 4-byte signed integer (DBTYPE_I4).
            elif fieldtype == adIUnknown: type_code = BINARY # THINK ABOUT THIS
            # A pointer to an IUnknown interface on an OLE object (DBTYPE_IUNKNOWN).
            elif fieldtype == adLongVarBinary: type_code = BINARY
            # A long binary value (Parameter object only).
            elif fieldtype == adLongVarChar: type_code = STRING
            # A long String value (Parameter object only).
            elif fieldtype == adLongVarWChar: type_code = STRING
            # A long null-terminated string value (Parameter object only).
            elif fieldtype == adNumeric: type_code = NUMBER
            # An exact numeric value with a fixed precision and scale (DBTYPE_NUMERIC).
            elif fieldtype == adSingle: type_code = NUMBER
            # A single-precision floating point value (DBTYPE_R4).
            elif fieldtype == adSmallInt: type_code = NUMBER
            # A 2-byte signed integer (DBTYPE_I2).
            elif fieldtype == adTinyInt: type_code = NUMBER
            # A 1-byte signed integer (DBTYPE_I1).
            elif fieldtype == adUnsignedBigInt: type_code = NUMBER
            # An 8-byte unsigned integer (DBTYPE_UI8). 
            elif fieldtype == adUnsignedInt: type_code = NUMBER
            # A 4-byte unsigned integer (DBTYPE_UI4). 
            elif fieldtype == adUnsignedSmallInt: type_code = NUMBER
            # A 2-byte unsigned integer (DBTYPE_UI2). 
            elif fieldtype == adUnsignedTinyInt: type_code = NUMBER
            # A 1-byte unsigned integer (DBTYPE_UI1). 
            elif fieldtype == adUserDefined: type_code = UNKNOWN # THINK ABOUT THIS
            # A user-defined variable (DBTYPE_UDT). 
            elif fieldtype == adVarBinary: type_code = BINARY
            # A binary value (Parameter object only).
            elif fieldtype == adVarChar: type_code = STRING
            # A String value (Parameter object only). 
            elif fieldtype == adVariant: type_code = UNKNOWN
            # An Automation Variant (DBTYPE_VARIANT). 
            elif fieldtype == adVarWChar: type_code = STRING
            # A null-terminated Unicode character string (Parameter object only). 
            elif fieldtype == adWChar: type_code = STRING
            # A null-terminated Unicode character string (DBTYPE_WSTR). 
            
            display_size = field.ActualSize
            internal_size = field.DefinedSize
            precision = field.Precision
            scale = field.NumericScale
            null_ok = field.Attributes & adFldMayBeNull

            # add this column to the description list
            description.append((name,type_code,display_size,internal_size,
                  precision,scale,null_ok))
        # return the list of all descriptions
        return description
      
    def close(self):
        """Close the cursor now (rather than whenever __del__ is called)."""

        # if called before Execute, will fail        
        self.rs.Close()

    def fetchone(self):
        """Fetch the next row of a query result set, returning a single sequence, or None when no more data is available"""
        # if called before Execute, will fail        
        if self.rs.EOF: return None
        row = [] 
        for col in range(len(self.Fields)):
            fieldvalue = self.Fields[col].Value
            row.append(fieldvalue)
        self.rs.MoveNext()
        return row

    def fetchall(self):
        """Fetch all (remaining) rows of a query result, returning them as a sequence of sequences (e.g. a list of tuples)."""
        
        # if called before Execute, will fail        
        rows = []
        # if we're at the end of the recordset, simply return the rows we have so far
        while not self.rs.EOF:
            # fetch the values for this row, and add the row to the list
            row = []
            for col in range(len(self.Fields)):
                row.append(self.Fields[col].Value)
            rows.append(row)
            self.rs.MoveNext()
        return rows

    def fetchmany(self, size=None):
        """Fetch the next set of rows of a query result, returning a sequence of sequences (e.g. a list of tuples).
        An empty sequence is returned when no more rows are available."""
        
        # if called before Execute, will fail        
        if size == None: size = self.arraysize
        rows = []
        for rownumber in range(size):
            # if we're at the end of the recordset, simply return the rows we have so far
            if self.rs.EOF:
                return rows
            # fetch the values for this row, and add the row to the list
            row = []
            for col in range(len(self.Fields)):
                row.append(self.Fields[col].Value)
            rows.append(row)
            self.rs.MoveNext()
        return rows
    
    def executemany(self, operation, parameters=None):
        """Execute operation (query or command) against all parameter sequences or mappings
        found in the sequence seq_of_parameters."""
        size = len(parameters)
        self.rsList = []
        self.rsListPos = 0
        for rownumber in range(size):
            rs = win32com.client.Dispatch("ADODB.Recordset")
            Query = operation % parameters[rownumber]
            rs.Open(Query, ActiveConnection = self.PassConn)
            self.rsList.append(rs)
        self.rs = self.rsList[0]
        # cache the fields. this must be done before describefields
        self.Fields = [self.rs.Fields.Item(col) for col in range(self.rs.Fields.Count)] 
        # initialize the description for the first rowset
        self.description = self.describefields()

    def nextset(self):
        """make the cursor skip to the next available set,
        discarding any remaining rows from the current set.
        If there are no more sets, returns None. Otherwise, returns true"""
        self.rsListPos += 1
        if self.rsListPos >= len(self.rsList):
            return None
        self.rs = self.rsList[self.rsListPos]
        # cache the fields. this must be done before describefields
        self.Fields = [self.rs.Fields.Item(col) for col in range(self.rs.Fields.Count)] 
        # redo the description as this rowset might be different
        self.description = self.describefields()
        return 1

        # do we need this? in case it closes down?
        # if self.rs.State == 0: self.rs.Open()

    def getrowcount(self):
        # if called before Execute, will fail
        if self.rs.State == 0:
            self.rs.Open()
            return self.rs.RecordCount
            self.rs.Close()
        if self.rs.State != 0:
            return self.rs.RecordCount

    def __getattr__(self, Name):
        """Override the attribute rowcount, so we can have a read-only attribute that calls a procedure"""
        if Name in self.__dict__:
            return self.__dict__[Name]
        elif Name == 'rowcount':
            return self.getrowcount()

#Testing
def testcase(dsn,user=None,password=None,host=None,database=None,provider=None,sql=None, sqlBase=None, sqlParam=None):
    theConnection = connect(dsn,user=user,password=password,host=host,database=database,provider=provider)
    theCursor = theConnection.cursor()
    print "Execute Test:"
    theCursor.execute(sql)
    print theCursor.fetchone()
    print theCursor.fetchmany(100)
    print theCursor.fetchall()
    print theCursor.rowcount
    print "Executemany Test (list of parameters):"
    theCursor.executemany(sqlBase, sqlParam)
    while 1:
        print theCursor.fetchall()
        if theCursor.nextset() is None: break
    theCursor.close()
    theConnection.close()

