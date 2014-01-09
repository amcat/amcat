from __future__ import print_function
import logging
log = logging.getLogger(__name__)

class ProgressMonitor(object):
    def __init__(self, total=100, message="In progress"):
        self.total = 100
        self.message = message
        self.worked = 0
        self.listeners = []

    def update(self, units, message=None):
        self.worked += units
        if message: self.message = message
        self.do_update()

    def do_update(self):
        self.percent = int(100. * self.worked / self.total)
        log.info("[{self.percent}%] {self.worked} / {self.total} {self.message}".format(**locals()))
        for listener in self.listeners:
            listener(self)

    def add_listener(self, func):
        self.listeners.append(func)

    def remove_listener(self, func):
        self.listeners.remove(func)

class NullMonitor(ProgressMonitor):
    def update(self, *args, **kargs):
        pass
        
if __name__ == '__main__':
    from amcat.tools import amcatlogging
    from django.conf import settings
    amcatlogging.setup()
    p = ProgressMonitor()
    def listen(pm):
        print (pm.percent, pm.message)
    p.add_listener(listen)
    p.update(15, "bezig")
    p.update(15, "nog steeds")
    p.remove_listener(listen)
    p.update(10, 'Ja')
    
