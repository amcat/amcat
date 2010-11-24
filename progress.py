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
Classes for keeping track of progress of jobs.

A ProgressMonitor is an object that keeps track of an amount of work that is
to be done. The job will call `worked' to indicate that work has been done,
and listeners on the monitor may react to that, e.g. by logging a message
every 10% of work.
"""

from __future__ import with_statement
import logging; log = logging.getLogger(__name__)
import amcatlogging
import toolkit
import re
from contextlib import contextmanager


STATE_NOTSTARTED, STATE_STARTED, STATE_DONE, STATE_ERROR = 0,1,2,3
STATE_LABELS = "not-started", "started", "done", "error"

class ProgressMonitor(object):
    """Eclipse-inspired ProgressMonitor

    Lifecycle of a progress monitor:
    - __init__()
    - start(taskname, #units)
    - worked(n) until sum(n) = #units
    - done()

    Progress can be delegated to a L{submonitor}
    """
    
    def __init__(self, name=None, taskname=None, units=100):
        """If taskname is given, calls L{start}"""
        self.exception = None
        self.name = name
        self.listeners = set()
        self.progress = 0 # progress so far
        self.units = None # total number of units to work
        self.state = STATE_NOTSTARTED # isdone? None = not started, False = started, True = done
        if taskname is not None:
            self.start(taskname, units)
        else:
            self.taskname = None

    def start(self, task="Task", units=100):
        """Start this monitor with the given name and #units to work

        Further calls to start will result in an error"""
        self._checkstate(STATE_NOTSTARTED)
        self.state = STATE_STARTED
        self.taskname = task
        self.units = units
        self._fire(True)
    def worked(self, n = 1):
        """Progess n units of work"""
        self._checkstate(STATE_STARTED)
        self.progress += n
        self._fire()
    def done(self):
        """Indicate that this progress monitor is done

        Further calls to worked will result in an error"""
        self._checkstate(STATE_STARTED)
        self.state = STATE_DONE
        self._fire(True)
    def error(self, exception):
        """Indicate that this monitor has encountered an error

        Further calls to worked or done will result in an error"""
        self.state = STATE_ERROR
        self.exception = exception
        self._fire(True)

    def checkError(self):
        """Raises the exception if the monitor has one, otherwise returns silently"""
        if self.exception is not None:
            if isinstance(self.exception, BaseException):
                raise self.exception
            else:
                raise Exception(self.exception)
    def percentDone(self):
        """@return: float representing the proportion of work done"""
        if self.progress is None: return None
        if self.units is None or self.units == 0: return None
        
        return float(self.progress) / self.units
    def isDone(self, checkError=True):
        """ check whether the progress is 'done', and raise except if error
        @param checkError: if False, do not check for (and raise) errors 
        @return: bool whether the progress is done or not"""
        self.checkError()
        return self.state == STATE_DONE
                
    def submonitor(self, workunits, name=None):
        """Create a submonitor to delegate part of the work to.
        The resulting monitor has to be start()ed before use!

        @param workunits: the number of units of parent work that the
          submonitor will do
        @param name: the name of the submonitor
        @return: a not-started ProgressMonitor object
        """
        m = ProgressMonitor(name)
        m.listeners.add(SubmonitorListener(self, workunits))
        return m

    def monitored(self, taskname, units, submonitorwork=None):
        return monitored(taskname, units, monitor=self, submonitorwork=submonitorwork)

    def _checkstate(self, state):
        """Check whether the monitor is in given state, raise Exception otherwise"""
        if self.state != state:
            raise IllegalMonitorStateException(self.state, state)
        
    def _fire(self, stateChanged=False):
        """Fire a messages to all listeners"""
        for listener in self.listeners:
            with amcatlogging.logExceptions(log):
                listener(self, stateChanged)

    def __str__(self):
        pd = self.percentDone()
        if pd is not None: pd = "%s%%" % int(pd*100)
        return "[PM %s: %s %s%s %s/%s %s]" % (self.name, self.taskname, STATE_LABELS[self.state],
                                              self.exception or "", self.progress, self.units, pd)

class SubmonitorListener(object):
    """Listener to connect a submonitor to its parent monitor"""
    def __init__(self, monitor, units):
        """
        @param monitor: the parent monitor
        @param units: the amount of parent-units that the full
          child is responsible for
        """
        self.monitor = monitor
        self.units = units
        self.sofar = 0
    def __call__(self, submon, stateChanged):
        # check if there is enough progress to warrant a
        # worked message to the parent monitor
        n = int(self.units * submon.percentDone())
        if n > self.sofar:
            self.monitor.worked(n - self.sofar)
            self.sofar = n
            
class TickLogListener(object):
    """Listener to log progress for a number of 'ticks' (ie 10%, 20% etc)"""
    def __init__(self, log, nticks):
        """
        @param log: the log to log the messages to
        @param nticks: the number of log points, e.g. 5 for 20%, 40% etc
        """
        self.log = log
        self.nticks = nticks
        self.lasttick = 0
    def __call__(self, monitor, stateChanged):
        # log message if stateChanged OR we reached a new 'tick'
        tick = int(self.nticks *  monitor.percentDone())
        if stateChanged or (tick > self.lasttick):
            msg = "[Progress"
            if monitor.name: msg += ":%s" % monitor.name
            msg += "] %s" % (monitor.taskname)
            if monitor.state == STATE_ERROR:
                msg += " error (%s)" % monitor.exception
            elif stateChanged:
                msg += " %s (%i units)" % (STATE_LABELS[monitor.state], monitor.units)
            else:
                msg += " %s/%s (%s%%)" % (monitor.progress, monitor.units, int(100*monitor.percentDone()))
            self.lasttick = tick
            fn, lineno, func = toolkit.getCaller(depth=3)
            self.log.handle(self.log.makeRecord(
                    self.log.name, logging.INFO,
                    fn, lineno, msg,
                    [], exc_info=None, func=func))

@contextmanager
def monitored(taskname, units, monitor=None, monitorname=None, submonitorwork=None):
    """ContextManager to help use a monitor for a task

    @taskname: the name of the task
    @units: the number of units work
    @monitor: if given, use this monitor instead of creating
      a new one
    @monitorname: if given, use this name when creating a (sub)monitor
    @submonitorwork: if this and monitor are given, create a
      submonitor of the given monitor representing this amount
      of work in the parent monitor
    """
    if monitor is None: monitor=ProgressMonitor(monitorname)
    elif submonitorwork: monitor=monitor.submonitor(submonitorwork, monitorname)
    monitor.start(taskname, units)
    try:
        yield monitor
    except StandardError, e: # don't catch generatorexit etc. from 2.6 this can be reverted to Exception?
        #log.exception(str(e))
        monitor.error(e)
    else:
        monitor.done()
            
def tickerate(seq, msg=None, log=None, logticks=10, monitor=None, monitorname=None, submonitorwork=None):
    if type(seq) not in (list, tuple, set):
        seq = list(seq)
    n = len(seq)
    if msg is None: msg = "Iteration"
    with monitored(msg, n, monitor, monitorname, submonitorwork) as m:
        if log: m.listeners.add(TickLogListener(log, logticks))
        for elem in seq:
            m.worked(1)
            yield elem
    
class IllegalMonitorStateException(Exception):
    """Exception to indicate that the monitor is in the incorrect state to
    perform the desired action"""
    def __init__(self, realstate, goalstate):
        Exception.__init__(self, "Monitor is required to be in state %s; but is in state %s" %
                           (STATE_LABELS[goalstate], STATE_LABELS[realstate]))

def readLog(logstr, monitorname=None, taskname=None):
    """Interpret the log messages of a TickLogListener

    @param logstr: the log string emitted by the listener
    @param monitorname: if given, the name of the progress monitor to search
    @param taskname: if given, the name of the task to search
    @return: a ProgressMonitor object
    """
    pattern = re.compile(r"INFO\] \[Progress:?(.*?)\]\s+(.*?)\s+(.*?)\s*\((.*?)\)")
    monitor = None
    # for now, interpret lines from top to bottom (reverse with break = more efficient, but who cares?)
    for line in logstr.split("\n"):
        m = pattern.search(line)
        if not m: continue # not a progress line
        mname, tname, action, units = m.groups()
        # check whether it is "our" monitor/task
        if (monitorname is not None) and mname != monitorname: continue
        if (taskname is not None) and tname != taskname: continue
        # start a monitor if needed
        if monitor is None:
            monitor = ProgressMonitor(mname or None)
            monitorname = mname
        #interpret action
        if action == "started":
            units = int(units.split()[0])
            monitor.progress = 0
            monitor.taskname = tname
            monitor.units = units
            monitor.state = STATE_STARTED
        elif action == "done":
            monitor.done()
        elif action == "error":
            monitor.error(units)   
        elif "/" in action:
            worked, total = map(int, action.split("/"))
            monitor.progress = worked
            monitor.taskname = tname
            monitor.units = total
            monitor.state = STATE_STARTED
        else:
            raise Exception("Cannot interpret action %r" % action)
    return monitor
        
if __name__ == '__main__':
    amcatlogging.setup()
    
    import StringIO
    sio= StringIO.StringIO()
    amcatlogging.setStreamHandler(sio)
    
    p = ProgressMonitor("x33")
    p.listeners.add(TickLogListener(log, 5))
    p.start("test")

    
    for i in range(40):
        p.worked()
    for i in tickerate(range(100), log=log, monitor=p, submonitorwork=30):
        pass#if i > 50: break
    p.done()
    p.error("!")

    print readLog(sio.getvalue(), "x33")
