from subprocess import *
import SocketServer, socket, dbtoolkit, config, toolkit


def expect(process, string):
    for i in range(len(string)):
        s = process.stdout.read(1)
        if s <> string[i]:
            process.stdin.close()
            r = process.stdout.read()
            raise Exception("Unexpected output! Expected %s, got \n%s<<ERROR HERE>>%s" % (string, string[:i],s+r))
        
def send(process, string):
    process.stdin.write(string)

PASSWD_CMD = "passwd %s"
PASSWD_PROMPT = "Enter new UNIX password: "
PASSWD_CONFIRM = "Retype new UNIX password: "
PASSWD_OK = "passwd: password updated successfully"
PASSWD_COMMAND = "PASSWD"
PASSWD_DONE = "PASSWD OK"
PASSWD_PORT = 50124
PASSWD_FORBIDDEN = "root","wva", "jcjacobi","nel"
PASSWD_SQLPASSWDCHANGED = '[FreeTDS][SQL Server]Password changed.'
PASSWD_PASSWORDFILE = "/root/passwd_password.txt"
PASSWD_SQLPASSWDFILE = "/root/sql_passwd.txt"
# make sure file is chmod 600 chown www-data !

def sql_password(user, newpwd, db=None, rootuser=None, rootpwd=None):
    if not db:
        if not rootuser: rootuser, rootpwd = open(PASSWD_SQLPASSWDFILE).read().strip().split(":")
        cnf = config.amcatConfig(rootuser, rootpwd)
        db = dbtoolkit.anokoDB(cnf)
    SQL = "exec sp_password @new=%s, @loginame=%s" % (
        toolkit.quotesql(newpwd), toolkit.quotesql(user))
    try:
        db.doQuery(SQL)
    except Exception, e:
        if not PASSWD_SQLPASSWDCHANGED in str(e): 
            raise e
    db.conn.commit()

def passwd(user, newpwd):
    p = Popen(PASSWD_CMD % user, shell=True, stdin=PIPE, stdout=PIPE, close_fds=True, stderr=STDOUT)
    expect(p, PASSWD_PROMPT)
    send(p, newpwd+"\n")
    expect(p, PASSWD_CONFIRM)
    send(p, newpwd+"\n")
    expect(p, PASSWD_OK)

class PasswdRequestHandler(SocketServer.StreamRequestHandler ):
    def handle(self):
        okpwd = self.server._SERVERPASSWORD_
        data = self.rfile.readline().strip().split("|")
        if len(data) <> 4:
            self.wfile.write("ERROR: Command should contain 4 |-delimited fields!")
            return
        command, spwd, un, pwd = data
        print "Incoming request: %s|****|%s|****" % (command, un)
        if command <> PASSWD_COMMAND:
            self.wfile.write("ERROR: Uknown command: %s"%command)
            return
        if spwd <> okpwd:
            print spwd, okpwd
            self.wfile.write("ERROR: Incorrect server password!")
            return
        if un in PASSWD_FORBIDDEN:
            self.wfile.write("ERROR: Cannot change password of selected user, sorry!")
            return
        try:
            passwd(un, pwd)
            sql_password(un, pwd)
            print "Changed password!"
            self.wfile.write(PASSWD_DONE)
        except Exception, e:
            print "Exception: %s" % e
            self.wfile.write("ERROR: %s"% e)


def getspwd():
    return open(PASSWD_PASSWORDFILE).read().strip()

#server host is a tuple ('host', port)
def server(spwd=None, port=PASSWD_PORT):
    if not spwd: spwd = getspwd()
    server = SocketServer.ThreadingTCPServer(('127.0.0.1', port), PasswdRequestHandler)
    server._SERVERPASSWORD_ = spwd
    server.serve_forever()

def remote(username, password, spwd=None, port=PASSWD_PORT):
    if not spwd: spwd = getspwd()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("localhost", port))
    sock.send("%s|%s|%s|%s\n" % (PASSWD_COMMAND, spwd, username, password))
    ok = sock.recv(1024).strip()
    sock.close()
    if ok <> PASSWD_DONE:
        raise Exception("Unexpected server response: %s" % ok)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print """Usages
        python passwd.py SERVER [serverpassword]
        python passwd.py CLIENT user password [serverpassword]
        python passwd.py user passwd"""
        sys.exit(1)
    if sys.argv[1] == "SERVER":
        spwd = None
        if len(sys.argv) > 2: spwd = sys.argv[2]
        print "Setting up server..."
        server(spwd)
    if sys.argv[1] == "CLIENT":
        un, pwd = sys.argv[2:4]
        print "Changing password for user %s" % (un, )
        spwd = None
        if len(sys.argv) > 4: spwd = sys.argv[4]
        remote(un, pwd, spwd)
    else:
        print "Changing password for user %s" % (un, )
        un, pwd = sys.argv[1:]
        passwd(un, pwd)
        sql_password(un, pwd)    





