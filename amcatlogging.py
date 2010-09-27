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
import StringIO
import thread
import sys

_CONTEXT = threading.local()
_HANDLER_IS_SET = False

_FORMAT = "[%(pathname)s:%(lineno)d %(application)s/%(user)s/%(host)s %(levelname)s] %(message)s"
_DATE_FORMAT = "[%(asctime)s %(pathname)s:%(lineno)d %(application)s/%(user)s/%(host)s %(levelname)s] %(message)s"

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

def _getFormatter(date=False):
    return AmcatFormatter(date)
#return logging.Formatter(_DATE_FORMAT if date else _FORMAT)

def _setSyslogHandler(logger):
    """Make sure that the sysloghandler is set on the amcat logger"""
    global _HANDLER_IS_SET
    if _HANDLER_IS_SET: return
    h = logging.handlers.SysLogHandler(address="/dev/log", facility="local0")
    h.setFormatter(_getFormatter())
    h.setLevel(logging.WARNING)
    logger.addHandler(h)
    _HANDLER_IS_SET = True
  
def getLogger(application=None, user=None, host=None):
    """Retrieve the amcat logger and make sure that the syslog handler is attached

    If application is given, L{setContext} will be run
    """ 
    logger = logging.getLogger("amcat")
    _setSyslogHandler(logger)
    if application is not None:
        setContext(application, user, host)
    return logger

def setContext(application, user=None, host=None):
    """Set the Context for the current thread

    The application name, user, and host (all strings) will be set
    for this thread and included in subsequent logging messages.
    """
    _CONTEXT.application = application
    _CONTEXT.user = user
    _CONTEXT.host = host

def debug(msg, level, depth=1, fn=None, lineno=None, func=None, exc_info=None):
    """Create a log record in the amcat logger with specified level and msg.

    Caller info is taken from the stack at the given depth using L{toolkit.getCaller}
    """
    logger = getLogger()
    if fn is None:
        fn, lineno, func = toolkit.getCaller(depth)
    extra = dict((k, getattr(_CONTEXT, k, None)) for k in ["application","user","host"])
    rec = logger.makeRecord("amcat", level, fn, lineno, msg, [], exc_info, func=func, extra=extra)
    logger.handle(rec)

def warn(msg, level=logging.WARN, depth=2, **kargs):
    """Convenience method to call debug(level=logging.WARN)"""
    debug(msg, level=level, depth=depth, **kargs)
    
def info(msg, level=logging.INFO, depth=2, **kargs):
    """Convenience method to call debug(level=logging.INFO)"""
    debug(msg, level=level, depth=depth, **kargs)

def exception(msg=None, level=logging.ERROR, depth=2, exc_info=None, **kargs):
    if exc_info is None: exc_info = sys.exc_info()
    if msg is None: msg = str(exc_info[1])
    debug(msg, level=level, depth=depth, exc_info = exc_info, **kargs)
    
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
    """Collect the log messages in this context into a StringIO

    >>> with collect() as l:
          pass # do something
        print format(l)
    """
    mh = MemoryHandler(destination)
    logger = getLogger()
    logger.addHandler(mh)
    logger.addFilter(CurrentThreadFilter())
    try:
        yield mh.destination
    finally:
        logger.removeHandler(mh)

@contextmanager
def logExceptions(basetype=Exception):
    """Creates a try/catch block that logs exceptions"""
    try:
        yield
    except basetype:
        exception(depth=4)
        
def format(records, date=True):
    if isinstance(records, logging.LogRecord):
        records = (records,)
    return "\n".join(_getFormatter(date).format(r) for r in records)


if __name__ == '__main__':
    setContext("amcat2", "piet", "192.168.1.1")
    warn("Dit is een eerste waarschuwing")
    with collect() as s:
        warn("Dit is een waarschuwing")
        info("Dit is info")
    print "Done collecting, printing:"
    print s.getvalue()
    print "---"
