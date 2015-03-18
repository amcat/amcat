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
        log.info("[{self.percent}%] {self.worked} / {self.total} {self.message!r}".format(**locals()))
        for listener in self.listeners:
            listener(self)

    def add_listener(self, func):
        self.listeners.append(func)

    def remove_listener(self, func):
        self.listeners.remove(func)


class NullMonitor(ProgressMonitor):
    def update(self, *args, **kargs):
        pass

