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

This module contains a number of generally useful auxilliary functions related to logging:
- The L{collect} contextmanager can be used to collect all log message from the body
- The L{logExceptions} contextmanager can be used to log exceptions from its body
- L{format} formats one or more logrecords to a string
 

Additionally, it contains a number of useful classes for managing logging
- L{AmcatFormatter} gives a pretty format to log messages
- L{ContextInjectionFilter} uses a thread-specific context to add the extra
  context from L{setContext} to log records
- L{ModuleLevelFilter} uses the module-level L{DEBUG_MODULES} and L{INFO_MODULES}
  to filter >= warn unless a record is in a modules on those lists, which it 
  can place itself on using L{debugModule} and L{infoModule}

In general, amcat modules should:
1. Normal (library) modules should not use this module
   (except the auxilliary functions and debugModule)
2. Applications (e.g. the web site, daemons, scripts) should install a handler on
   the root by calling L{setSyslogHandler} or L{setStreamHandler}
3. Thread-based applications (e.g. the web site) can call setContext to add useful
   extra information to all log records from that thread.
"""
from __future__ import unicode_literals, print_function, absolute_import

from contextlib import contextmanager
import logging
from logging.handlers import SysLogHandler
import threading
import thread
import tempfile
import os.path

from amcat.tools import toolkit

_THREAD_CONTEXT = threading.local()
CONTEXT_FIELDS = ['application', 'user', 'host']

QUIET_MODULES = set()
DEBUG_MODULES = set()
INFO_MODULES = set(['__main__', 'ticker'])

logging.getLogger().setLevel(logging.DEBUG)

class SilentException(Exception):
    """Exception subclass that will be suppressed by the ModuleLevelFilter"""
    pass

class AmcatFormatter(logging.Formatter):
    """
    Formatter to insert file, line, and level
    also includes 'context fields' that have been inserted
    """
    def __init__(self, date=False):
        logging.Formatter.__init__(self)
        self.date = date
    def format(self, record):
        s = "["
        if self.date: s += self.formatTime(record)[:19] +" "
        s += "%(pathname)s:%(lineno)d " % record.__dict__
        for f in 'application', 'user', 'host':
            s2 = getattr(record, f, None)
            if s2: s += s2 +" "
        s += "%(levelname)s]" % record.__dict__
        if isinstance(record.msg, unicode):
            s += record.msg
        else:
            s += unicode(record.msg, encoding="latin-1")
        if getattr(record, 'exc_info', None):
            s += "\n"+self.formatException(record.exc_info)
        return s

class ContextInjectingFilter(logging.Filter):
    """
    Filter to inject context from the current thread using the _THREAD_CONTEXT
    """
    def filter(self, record):
        for field in CONTEXT_FIELDS:
            val = getattr(_THREAD_CONTEXT, field, None)
            if val is not None:
                record.field = val
        return True

class ModuleLevelFilter(logging.Filter):
    """
    Filter to ignore errors based on message level and module level
    """
    def filter(self, record):
        if record.exc_info and issubclass(record.exc_info[0], SilentException): return False
        #print record, record.name
        if record.levelno < logging.ERROR and record.name in QUIET_MODULES: return False
        if record.levelno >= logging.WARNING: return True
        if record.levelno >= logging.INFO and record.name in INFO_MODULES: return True
        if record.levelno >= logging.DEBUG and record.name in DEBUG_MODULES: return True
        return False

def quiet_module(*modules):
    """Add the given modules to the list of modules from which to report only errors"""
    _addModulesToSet(QUIET_MODULES, *modules)
def info_module(*modules):
    """Add the given modules to the list of modules from which to report also info messages"""
    _addModulesToSet(INFO_MODULES, *modules)
def debug_module(*modules):
    """Add the given modules to the list of modules from which to report all messages (inc debug)"""
    _addModulesToSet(DEBUG_MODULES, *modules)
# backwards compatability
debugModule, infoModule, quietModule = debug_module, info_module, quiet_module
    
def _addModulesToSet(targetset, *modules):
    """Add the given modules to the targetset"""
    if not modules: modules = [toolkit.getCallingModule(depth=2)]
    targetset.update(modules)

    
def setSyslogHandler():
    """Add a sysloghandler to the root logger with contextinjecting and module level filters"""
    root = logging.getLogger()
    h = SysLogHandler(address=b"/dev/log", facility=b"local0")
    h.setFormatter(AmcatFormatter())
    h.addFilter(ContextInjectingFilter())
    h.addFilter(ModuleLevelFilter())
    root.addHandler(h)

def setStreamHandler(*args, **kargs):
    """Add a StreamHandler to the root logger with module level filters"""
    root = logging.getLogger()
    h = logging.StreamHandler(*args, **kargs)
    h.setFormatter(AmcatFormatter(date=True))
    h.addFilter(ModuleLevelFilter())
    root.addHandler(h)

def setFileHandler(filename, directory=None, filesize=50):
    """add a RotatingFileHanlder to the root logger with module level filters"""
    root = logging.getLogger()
    if directory is None: directory = tempfile.gettempdir()
    fn = os.path.join(directory, filename)
    
    h = logging.handlers.RotatingFileHandler(filename=fn, maxBytes = 1024*1024*filesize, backupCount = 3)
    h.setFormatter(AmcatFormatter(date=True))
    h.addFilter(ModuleLevelFilter())
    root.addHandler(h)


@contextmanager
def streamHandler(stream):
    """
    Log handler that emits messsages to the given stream
    """
    root = logging.getLogger()
    h = logging.StreamHandler(stream)
    h.setFormatter(AmcatFormatter(date=True))
    h.addFilter(ModuleLevelFilter())
    try:
        root.addHandler(h)
        stream.write("INSTALLED HANDLER")
        yield h
    finally:
        root.removeHandler(h)
        stream.write("REMOVED HANDLER")



        
def setup():
    """
    Convenience function for command line scripts.
    Sets up stream handler and returns a logger to use.
    """
    setStreamHandler()
    return logging.getLogger('__main__')
    
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
    mh.setLevel(level)
    mh.addFilter(CurrentThreadFilter())
    #mh.addFilter(ModuleLevelFilter())
    logger = logging.getLogger()
    logger.addHandler(mh)
    try:
        yield mh.destination
    finally:
        logger.removeHandler(mh)

@contextmanager
def logExceptions(msg="Exception occured", logger=None, basetype=Exception):
    """Creates a try/catch block that logs exceptions"""
    try:
        yield
    except basetype:
        if not logger:
            logger = logging.getLogger(toolkit.getCallingModule())
        logger.exception(msg)
        
def format_records(records, date=True):
    """Format a set of records using the AmcatFormatter"""
    fmt = AmcatFormatter(date).format
    if isinstance(records, logging.LogRecord):
        records = (records,)
    return "\n".join(fmt(r) for r in records)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestLogging(amcattest.PolicyTestCase):
    PYLINT_IGNORE_EXTRA = "W0703", 
    
    def testCollect(self):
        """Test whether collect() properly collects log records"""
        with collect() as s:
            logging.info("debug message")
            logging.info("debug message")
        self.assertEqual(2, len(s))
        self.assertIn("INFO] debug message", format_records(s))

    def testCollectException(self):
        """Test whether collect properly collect exceptions?"""
        with collect() as s:
            try:
                _x = 1/0
            except ZeroDivisionError:
                logging.exception("Exception")
        self.assertIn('integer division or modulo by zero', format_records(s))
        self.assertIn('_x = 1/0', format_records(s))
        
    def testLogExceptions(self):
        """Test whether logExceptions() works and does not raise the exception"""
        with collect() as s:
            with logExceptions():
                raise Exception("!")
        self.assertEqual(len(s), 1)
        self.assertIn('raise Exception("!")', format_records(s))
        
    def testModuleLevel(self):
        """Test whether the module level filter works"""
        log = logging.getLogger(__name__)
        log.addFilter(ModuleLevelFilter())
        infoModule()
        with collect() as s:
            log.debug("debug message")
            log.info("info message")
            log.warn("warn message")
        self.assertEqual(len(s), 2)
        debugModule()
        with collect() as s:
            log.debug("debug message")
            log.info("info message")
            log.warn("warn message")
        self.assertEqual(len(s), 3)
            
