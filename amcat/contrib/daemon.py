#!/usr/bin/env python

"""
Script from http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
Public domain
[WvA] changed run method to a flexible 'target' parameter
[Martijn] also kill children spawned by multiprocessing
"""
 
import subprocess
import sys, os, time, atexit
from signal import SIGTERM
 
class Daemon:
    """
    A generic daemon class.
   
    @param target: the function to be called in the daemonised process
    """
    def __init__(self, target, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.target = target
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
   
    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            print 123
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)
        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        
        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)
   
    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)
        
        # Start the daemon
        self.daemonize()
        self.target()

    def _kill(self, pid):
        # Try killing the daemon process       
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                return
            else:
                print str(err)
                sys.exit(1)

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Kill process and its children
        ps = subprocess.Popen(
            "ps -o pid --ppid %d --noheaders" % pid,
            shell=True, stdout=subprocess.PIPE
        )

        ps_out = ps.stdout.read()
        ps_ret = ps.wait()

        if ps_ret != 0 and ps_out.strip():
            message = "Could not find children! Command `ps` returned %s\n"
            sys.stderr.write(message % ps_ret)

        children = [int(p) for p in ps_out.split("\n")[:-1]]

        for p in [pid] + children:
            self._kill(p)

        self.delpid()


    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()
