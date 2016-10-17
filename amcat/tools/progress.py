import logging

log = logging.getLogger(__name__)


class ProgressMonitor(object):
    def __init__(self, total=100, message="In progress", name=None, log=True):
        self.total = total
        self.message = message
        self.worked = 0
        self.listeners = []
        self.log = log
        self.name = name

    def update(self, units=1, message=None):
        self.worked += units
        if message: self.message = message
        self.do_update()

    def do_update(self):
        self.percent = int(100. * self.worked / self.total)
        if self.log:
            name = "{self.name}: ".format(**locals()) if self.name else ""
            log.info("[{name}{self.percent}%] {self.worked} / {self.total} {self.message!r}"
                     .format(**locals()))
        for listener in self.listeners:
            listener(self)

    def add_listener(self, func):
        self.listeners.append(func)

    def remove_listener(self, func):
        self.listeners.remove(func)

    def submonitor(self, units, *args, **kargs):
        return SubMonitor(self, units, *args, **kargs)
        
class SubMonitor(ProgressMonitor):
    def __init__(self, super_monitor, super_units, log=False, *args, **kargs):
        self.super_monitor = super_monitor
        self.super_units = super_units
        super(SubMonitor, self).__init__(*args, log=False, **kargs)

    def update(self, units=1, message=None):
        s = int(float(units) / self.total * self.super_units)
        self.super_monitor.update(s, message)
        super(SubMonitor, self).update(units, message)


class NullMonitor(ProgressMonitor):
    def update(self, *args, **kargs):
        pass

