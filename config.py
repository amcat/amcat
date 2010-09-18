import os, os.path

__PASSWD_FILE = '.sqlpasswd'

class Configuration:
    def __init__(self, username, password, host="anoko", database="anoko", driver=None, useDSN=False, keywordargs=False):
        if not driver: raise Exception("No driver!")
        self.host = host
        self.username = username
        self.password = password
        self.database = database
        self.driver = driver
        self.drivername = driver.__name__
        self.useDSN = useDSN 
        self.keywordargs = keywordargs

    def connect(self, *args, **kargs):
        if self.useDSN:
            return self.driver.connect("DSN=%s" % self.host, user=self.username, password=self.password, *args, **kargs) 
        elif self.keywordargs:
            return self.driver.connect(user=self.username, password=self.password, database=self.database, host=self.host)
        else:
            return self.driver.connect(self.host, self.username, self.password, *args, **kargs)
        
def default(**kargs):
    homedir = os.getenv('HOME')

    if not homedir:
        if 'SERVER_SOFTWARE' in os.environ or 'username' in kargs or 'use_app' in kargs:
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

def amcatConfig(username = "app", password = "eno=hoty", easysoft=False, database="anoko", use_app=None):
    
    if easysoft:
        host = "Easysoft-AmcatDB"
        #import pyodbc as driver
        import mx.ODBC.unixODBC as driver
        import dbtoolkit
        dbtoolkit.ENCODE_UTF8 = True
    else:
        host = "AmcatDB"
        import mx.ODBC.iODBC as driver
    return Configuration(username, password, host, driver=driver, database=database)#, kargs=easysoft)

if __name__ == '__main__':
    c = default()
    db = c.connect()
    print db
