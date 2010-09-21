import os, os.path, sys

__PASSWD_FILE = '.sqlpasswd'

class Configuration:
    def __init__(self, username, password, host="anoko", database="anoko", driver=None, useDSN=False,
                 keywordargs=False, setMxODBCErrorHandler=False):
        if not driver: raise Exception("No driver!")
        self.host = host
        self.username = username
        self.password = password
        self.database = database
        self.driver = driver
        self.drivername = driver.__name__
        self.useDSN = useDSN 
        self.keywordargs = keywordargs
        self.setMxODBCErrorHandler = setMxODBCErrorHandler

    def connect(self, *args, **kargs):
        if self.setMxODBCErrorHandler and "errorhandler" not in kargs:
            kargs["errorhandler"] = mxODBCErrorHandler()
        if self.useDSN:
            return self.driver.connect("DSN=%s" % self.host, user=self.username, password=self.password, *args, **kargs) 
        elif self.keywordargs:
            return self.driver.connect(user=self.username, password=self.password, database=self.database, host=self.host)
        else:
            return self.driver.connect(self.host, self.username, self.password, *args, **kargs)
            
        
def default(**kargs):
    homedir = os.getenv('HOME')
    if 'use_app' in kargs:
        return amcatConfig(**kargs)
    if not homedir:
        if 'SERVER_SOFTWARE' in os.environ or 'username' in kargs:
            return amcatConfig(**kargs)
        raise Exception('Could not determine home directory! Please specify the HOME environemnt variable')
    passwdfile = os.path.join(homedir, __PASSWD_FILE)
    if not os.access(passwdfile, os.R_OK):
        raise Exception('Could not find or read password file in "%s"!' % passwdfile)

    fields = open(passwdfile).read().strip().split(':')
    if 'username' not in kargs: kargs['username'] = fields[0]
    if 'password' not in kargs: kargs['password'] = fields[1]
    if os.name == 'nt':
        raise Exception("Windows currently not supported -- ask Wouter!")
    else:
        return amcatConfig(**kargs)

def amcatConfig(username = "app", password = "eno=hoty", easysoft=None, database="anoko", use_app=None):

    if easysoft is None:
        easysoft = sys.version_info[1] == 6

    if easysoft:
        host = "Easysoft-AmcatDB"
        #import pyodbc as driver
        import mx.ODBC.unixODBC as driver
        import dbtoolkit
        dbtoolkit.ENCODE_UTF8 = True
        setMxODBCErrorHandler = True
    else:
        host = "AmcatDB"
        import mx.ODBC.iODBC as driver
        setMxODBCErrorHandler = False
    return Configuration(username, password, host, driver=driver, database=database,setMxODBCErrorHandler=setMxODBCErrorHandler)#, kargs=easysoft)

MXODBC_IGNORE_WARNINGS = (15488, # X added to role Y
                          15341, # granted db access to X
                          15298, # new login created
                          15338, 15477, # rename warnings
                          )

class mxODBCErrorHandler(object):
    def __init__(self, ignore_warnings=MXODBC_IGNORE_WARNINGS):
        self.ignore_warnings = set(ignore_warnings)
        
    def __call__(self, connection, cursor, errorclass, errorvalue):
        """ mxODBC error handler.
        The error handler reports all errors and warnings
        using exceptions and also records these in
        connection.messages as list of tuples (errorclass,
        errorvalue), except for the ignore_warnings
        """
        # Append to messages list
        if cursor is not None:
            cursor.messages.append((errorclass, errorvalue))
        elif connection is not None:
            connection.messages.append((errorclass, errorvalue))
        # Ignore specified warnings
        errno = errorvalue[1]
        if errno in self.ignore_warnings:
            return
        # Raise the exception
        raise errorclass, errorvalue


if __name__ == '__main__':
    c = default()
    db = c.connect()
    print db
