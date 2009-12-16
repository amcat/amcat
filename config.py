import os, os.path

__PASSWD_FILE = '.sqlpasswd'

class Configuration:
    def __init__(this, username, password, host="anoko", database="anoko", driver=None):
        if not driver: raise Exception("No driver!")
        this.host = host
        this.username = username
        this.password = password
        this.database = database
        this.driver = driver
        this.drivername = driver.__name__

    def connect(this, *args, **kargs):
        return this.driver.connect(this.host, this.username, this.password, *args, **kargs)
        
        
        
def default():
    homedir = os.getenv('HOME')

    if not homedir:
        if 'SERVER_SOFTWARE' in os.environ:
            return amcatConfig()
        raise Exception('Could not determine home directory! Please specify the HOME environemnt variable')
    passwdfile = os.path.join(homedir, __PASSWD_FILE)
    if not os.access(passwdfile, os.R_OK):
        raise Exception('Could not find or read password file in "%s"!' % passwdfile)

    fields = open(passwdfile).read().strip().split(':')
    un, password = fields[:2]
    host = len(fields) > 2 and fields[2] or None
    if os.name == 'nt':
        raise Exception("Windows currently not supported -- ask Wouter!")
    else:
        return amcatConfig(un, password, host)

def amcatConfig(username = "app", password = "eno=hoty", host=None):
    if not host: host = "AmcatDB"
    import mx.ODBC.iODBC as driver
    return Configuration(username, password, host, driver=driver)

if __name__ == '__main__':
    c = default()
    print "Config: host %s, username %s, passwd %s.., attempting to connect" % (c.host, c.username, c.password[:2])
    db = c.connect()
    print db
