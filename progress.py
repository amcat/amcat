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


STATE_NOTSTARTED, STATE_STARTED, STATE_DONE = 0,1,2
STATE_LABELS = "not-started", "started", "done"

class ProgressMonitor(object):
    """Eclipse-inspired ProgressMonitor

    Lifecycle of a progress monitor:
    - __init__()
    - start(taskname, #units)
    - worked(n) until sum(n) = #units
    - done()

    Progress can be delegated to a L{submonitor}
    """
    
    def __init__(self, taskname=None, units=100):
        """If taskname is given, calls L{start}"""
        self.listeners = set()
        self.progress = 0 # progress so far
        self.units = None # total number of units to work
        self.state = STATE_NOTSTARTED # isdone? None = not started, False = started, True = done
        if taskname is not None:
            self.start(taskname, units)
        else:
            self.taskname = None

    def start(self, task="Task", units=100):
        """Start this monitor with the given name and #units to work"""
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
        """Indicate that this progress monitor is done"""
        self._checkstate(STATE_STARTED)
        self.state = STATE_DONE
        self._fire(True)

    def _checkstate(self, state):
        """Check whether the monitor is in given state, raise Exception otherwise"""
        if self.state != state:
            raise IllegalMonitorStateException(self.state, state)
        
    def _fire(self, stateChanged=False):
        """Fire a messages to all listeners"""
        for listener in self.listeners:
            with amcatlogging.logExceptions(log):
                listener(self, stateChanged)

    def percentDone(self):
        """@return: float representing the proportion of work done"""
        return float(self.progress) / self.units
    def isDone(self):
        """@return: bool whether the progress is done or not"""
        return self.state == STATE_DONE
                
    def submonitor(self, workunits):
        """Create a submonitor to delegate part of the work to.
        The resulting monitor has to be start()ed before use!

        @param workunits: the number of units of parent work that the
          submonitor will do
        @return: a not-started ProgressMonitor object
        """
        m = ProgressMonitor()
        m.listeners.add(SubmonitorListener(self, workunits))
        return m

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
            msg = "progress %s" % (monitor.taskname)
            if stateChanged:
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
def monitored(name, units, monitor=None, submonitorwork=None):
    """ContextManager to help use a monitor for a task

    @name: the name of the task
    @units: the number of units work
    @monitor: if given, use this monitor instead of creating
      a new one
    @submonitorwork: if this and monitor are given, create a
      submonitor of the given monitor representing this amount
      of work in the parent monitor
    """
    if monitor is None: monitor=ProgressMonitor()
    elif submonitorwork: monitor=monitor.submonitor(submonitorwork)
    monitor.start(name, units)
    try:
        yield monitor
    finally:
        monitor.done()
            
def tickerate(seq, msg=None, log=None, logticks=10, monitor=None, submonitorwork=None):
    if type(seq) not in (list, tuple, set):
        seq = list(seq)
    n = len(seq)
    if msg is None: msg = "Iteration"
    with monitored(msg, n, monitor, submonitorwork) as m:
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

def readLog(logstr, name, monitor=None):
    if monitor is None: monitor = ProgressMonitor()
    pattern = re.compile(r"INFO] progress %s\s+(.*?)\s*\((.*\))" % name)
    for line in logstr.split("\n"):
        m = pattern.search(line)
        if not m: continue
        action, units = m.groups()
        if action == "started":
            units = int(units.split()[0])
            monitor.start(name, units)
        elif action == "done":
            monitor.done()
        else:
            worked = int(action.split("/")[0])
            monitor.progress = worked
    return monitor
        
if __name__ == '__main__':
    amcatlogging.setup()
    
    import StringIO
    sio= StringIO.StringIO()
    amcatlogging.setStreamHandler(sio)
    
    p = ProgressMonitor()
    p.listeners.add(TickLogListener(log, 5))
    p.start("test")

    
    for i in range(40):
        p.worked()
    for i in tickerate(range(100), log=log, monitor=p, submonitorwork=30):
        pass#if i > 50: break
    p.done()

    print readLog(sio.getvalue(), "test").percentDone()
