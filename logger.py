import time

class Logger:
    def __init__(self,logfile = '/tmp/pythonlog'):
        self.logfile = open(logfile,'a')
        self.logfile.write('\n\nNew log session\ncum\tstep\tname')
        self.t = time.time()
        self.init = self.t

    def write(self,str):
        now = time.time()
        thisstep = now - self.t
        cum = now - self.init

        self.logfile.write('%6.2f\t%6.2f\t%s\n' % (cum, thisstep, str))

        self.t = time.time()

class nolog:
    def write(*args, **kargs):
        pass

log = nolog()
#log = Logger()
