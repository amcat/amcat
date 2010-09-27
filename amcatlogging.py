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

"""
Utility methods to use the python logging framework in AmCAT
"""

from __future__ import with_statement

from contextlib import contextmanager
import logging
import logging.handlers
import threading
import toolkit
import thread
import sys
import inspect

_THREAD_CONTEXT = threading.local()
CONTEXT_FIELDS = ['application','user','host']

DEBUG_MODULES = set()
INFO_MODULES = set(['__main__'])

logging.getLogger().setLevel(logging.DEBUG)

class AmcatFormatter(logging.Formatter):
    def __init__(self, date=False):
        logging.Formatter.__init__(self)
        self.date = date
    def format(self, record):
        s = "["
        if self.date: s += self.formatTime(record)[:19] +" "
        s += "%(pathname)s:%(lineno)d " % record.__dict__
        for f in 'application','user','host':
            s2 = getattr(record, f, None)
            if s2: s += s2 +" "
        s += "%(levelname)s] %(msg)s" % record.__dict__
        if getattr(record, 'exc_info', None):
            s += "\n"+self.formatException(record.exc_info)
        return s

class ContextInjectingFilter(logging.Filter):
    def filter(self, record):
        for field in CONTEXT_FIELDS:
            val = getattr(_THREAD_CONTEXT, field, None)
            if val is not None:
                record.field = val
        return True

class ModuleLevelFilter(logging.Filter):
    def filter(self, record):
        #print record, record.name
        if record.levelno >= logging.WARNING: return True
        if record.levelno >= logging.INFO and record.name in INFO_MODULES: return True
        if record.levelno >= logging.DEBUG and record.name in DEBUG_MODULES: return True
        return False

def infoModule():
    INFO_MODULES.add(toolkit.getCallingModule())

def debugModule():
    DEBUG_MODULES.add(toolkit.getCallingModule())

def setSyslogHandler():
    """Add a sysloghandler to the root logger with contextinjecting and module level filters"""
    root = logging.getLogger()
    h = logging.handlers.SysLogHandler(address="/dev/log", facility="local0")
    h.setFormatter(AmcatFormatter())
    h.addFilter(ContextInjectingFilter())
    h.addFilter(ModuleLevelFilter())
    root.addHandler(h)

def setStreamHandler():
    """Add a StreamHandler to the root logger with module level filters"""
    root = logging.getLogger()
    h = logging.StreamHandler()
    h.setFormatter(AmcatFormatter(date=True))
    h.addFilter(ModuleLevelFilter())
    root.addHandler(h)

def setContext(application, user=None, host=None):
    """Set the Context for the current thread

    The application name, user, and host (all strings) will be set
    for this thread and included in subsequent logging messages.
    """
    _THREAD_CONTEXT.application = application
    _THREAD_CONTEXT.user = user
    _THREAD_CONTEXT.host = host

   
class CurrentThreadFilter(logging.Filter):
    """Filter that only accepts log records from the current thread"""
    def filter(self, record):
        return record.thread == thread.get_ident()

class MemoryHandler(logging.Handler):
    """Simple Handler that stores a list of logrecords"""
    def __init__(self, dest=None):
        logging.Handler.__init__(self)
        self.destination = dest if (dest is not None) else []
    def emit(self, record):
        self.destination.append(record)

@contextmanager
def collect(level=logging.DEBUG, destination=None):
    """Collect the log messages in this context into a list

    >>> with collect() as l:
          pass # do something
        print format(l)
    """
    mh = MemoryHandler(destination)
    mh.setLevel(logging.DEBUG)
    mh.addFilter(CurrentThreadFilter())
    logger = logging.getLogger()
    logger.addHandler(mh)
    try:
        yield mh.destination
    finally:
        logger.removeHandler(mh)

@contextmanager
def logExceptions(logger=None, basetype=Exception):
    """Creates a try/catch block that logs exceptions"""
    try:
        yield
    except basetype, e:
        if not logger:
            logger = logging.getLogger(toolkit.getCallingModule())
        logger.exception(str(e))
        
def format(records, date=True):
    fmt = AmcatFormatter(date).format
    if isinstance(records, logging.LogRecord):
        records = (records,)
    return "\n".join(map(fmt, records))


if __name__ == '__main__':
    setStreamHandler()
    debugModule()
    log = logging.getLogger(__name__)
    print log.level, logging.DEBUG
    log.warning("warn")
    log.info("info")
    log.debug("debug")
    #logging.warning("test")
