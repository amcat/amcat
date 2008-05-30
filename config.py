import os, os.path

__PASSWD_FILE = '.sqlpasswd'

class Configuration:
    #def __init__(this, username, password, host="fswap02.scw.vu.nl", database="anoko", driver=None):
    def __init__(this, username, password, host="anoko", database="anoko", driver=None):
        this.host = host
        this.username = username
        this.password = password
        this.database = database
        if not driver:
            import Sybase as driver
        this.driver = driver
        this.drivername = driver.__name__

def default():
    homedir = os.getenv('HOME')
    if not homedir:
        if 'SERVER_SOFTWARE' in os.environ:
            return Configuration("app", "eno=hoty")
        raise Exception('Could not determine home directory! Please specify the HOME environemnt variable')
    passwdfile = os.path.join(homedir, __PASSWD_FILE)
    if not os.access(passwdfile, os.R_OK):
        raise Exception('Could not find or read password file in "%s"!' % passwdfile)

    fields = open(passwdfile).read().strip().split(':')
    un, password = fields[:2]
    host = len(fields) > 2 and fields[2] or None
    if os.name == 'nt':
        import toolkit
        toolkit._USE_CURSES=0
        driver = ODBCMSSQL()
    else:
        import Sybase as driver
        
    if host:
        return Configuration(un, password, host, driver=driver)
    else:
        return Configuration(un, password, driver=driver)

class ODBCMSSQL:
    """
    Wrapper around mx.ODBC to make it look like a regular
    database driver while using the driverconnect call
    """
    __name__ = "SQL over mx.ODBC"
    def connect(this, host, un, pwd, database=None):
        import mx.ODBC
        if database:
            return mx.ODBC.Windows.DriverConnect(r"Driver={SQL Server};Server=%(host)s;Database=%(database)s;uid=%(un)s;pwd={%(pwd)s};" % locals(), 0)
        else:
            return mx.ODBC.Windows.DriverConnect(r"Driver={SQL Server};Server=%(host)s;uid=%(un)s;pwd={%(pwd)s};" % locals(), 0)



if __name__ == '__main__':
    c = default()
    print "Config: host %s, username %s, passwd %s..." % (c.host, c.username, c.password[:2])


