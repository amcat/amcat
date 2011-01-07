from __future__ import print_function, absolute_import
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

import os, os.path

import logging; log = logging.getLogger(__name__)

class Configuration(object):
    def __init__(self, username, password, host=None, database=None):
        self.username = username
        self.password = password
        self.host = host
        self.database = database
    def connect(self, **kargs):
        raise NotImplementedError()
    
    def _doConnect(self, driver, **kargs):
        log.debug("Connecting to %s using %s" % (driver, self))
        return driver.connect(self.host, self.username, self.password, **kargs)
    
    def __str__(self):
        d = dict(self.__dict__)
        d["password"] = '*' * len(d["password"])
        return "%s(%s)" % (self.__class__.__name__, ", ".join("%s=%r" % kv for kv in d.items()))

   
class SQLServer(Configuration):
    def __init__(self, username, password, host="AmcatDB", database="anoko"):
        Configuration.__init__(self, username, password, host, database)
        self.drivername = "mx.ODBC.iODBC"
        
    def connect(self, **kargs):
        import mx.ODBC.iODBC
        return self._doConnect(mx.ODBC.iODBC)
        
class EasySoft(Configuration):
    def __init__(self, username, password, host="Easysoft-AmcatDB", database="anoko"):
        Configuration.__init__(self, username, password, host, database)
        self.drivername = "mx.ODBC.unixODBC"
        
    def connect(self, **kargs):
        import mx.ODBC.unixODBC
        return self._doConnect(mx.ODBC.unixODBC,  errorhandler=mxODBCErrorHandler())

class PostgreSQL(Configuration):
    def __init__(self, username, password, host="localhost", database="amcat"):
        Configuration.__init__(self, username, password, host, database)
    def connect(self):
        import psycopg2
        # unicode handling: automatically get strings as unicode!
        import psycopg2.extensions
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
        return psycopg2.connect(user=self.username, password=self.password, database=self.database, host=self.host, **kargs)

__PASSWD_FILES = ['.amcatrc','.sqlpasswd']

def readconfig(fn):
    result = {}
    log.debug("Reading database configuration from %s" % fn)
    for i, line in enumerate(open(fn)):
        if ".sqlpasswd" in fn and i==0 and ":" in line:
            # assume 'old style' configuration
            un, pwd = line.split(":") 
            import sys
            driver = "EasySoft" if sys.version_info[1] == 6 else "SQLServer"
            return dict(driver=driver, username=un, password=pwd)
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip().lower()] = value.strip()
    return result

APP_CREDENTIALS = "app", "eno=hoty"

def getConfig(use_app=False, **kargs):
    if use_app:
        kargs["username"], kargs["password"] = APP_CREDENTIALS
    homedir = os.getenv('HOME')
    if "password" not in kargs and not homedir: raise Exception('Could not determine home directory! Please specify the HOME environemnt variable')
    for fn in __PASSWD_FILES:
        fn = os.path.join(homedir, fn)
        if os.access(fn, os.R_OK):
            d = readconfig(fn)
            d.update(kargs)
            kargs = d
            break
    if "password" not in kargs: 
        raise Exception("Could not find amcatdb configuration information in ~/.amcatrc or ~/.sqlpasswd")
    if "driver" not in kargs:
        raise Exception("No driver specified")
    return createConfig(**kargs)

def createConfig(driver, **kargs):
    if driver not in globals(): raise Exception("Unknown driver: %r" % driver)
    driverclass = globals()[driver]
    return driverclass(**kargs)
    
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
    from amcat.tools.logging import amcatlogging; amcatlogging.setup()
    amcatlogging.debugModule()
    db = getConfig().connect()
    print(db)
