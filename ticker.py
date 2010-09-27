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
Give progress feedback on the command line
"""

import time,  math, amcatlogging, logging, toolkit

class Ticker(object):
    """
    A Ticker object is called every iteration of some process, and
    displays a warning message for every N iterations
    """
    
    def __init__(self, interval = 10, markThread=True):
        """
        @param interval: give a warning message every C{interval} calls
        @param markThread: if True, display thread name unless MainThread
        """
        self.interval = interval
        self.i = 0
        self.start = time.time()
        self.last = time.time()
        self.markThread = markThread
        self.estimate = None

    def warn(self, msg, reset=False, interval = None, estimate=None, detail=0, depth=3, **kargs):
        """
        Display a warning message containing current iteration number

        @param msg: the message to display
        @param reset: if True, reset the current iteration number to zero
        @param interval: if given, set the interval of this ticker object
        @type estimate: int
        @param estimate: if given, compute an appropriate interval for the estimate
          amount of iterations, and suffix the message with the estimate and interval
        @type detail: int
        @param detail: if non-zero, decrease the interval by a factor 10^detail
          (e.g. give 10 times as many ticks)
        """
        if interval: self.interval = interval
        if estimate:
            self.reset()
            self.estimate = estimate
            magnitude = math.log10(estimate)
            if magnitude % 1 < 0.5: magnitude -= 1
            if detail: magnitude -= detail
            self.interval = 10**(int(magnitude))
            msg += " (%s steps / %s)" % (estimate, self.interval)

        self._doTick(msg, depth, **kargs)
        #self.last = now
        if reset: self.reset()

    def reset(self):
        """Reset the iteration count of this ticker to zero"""
        self.i = 0

    def _doTick(self, msg, depth=2, **kargs):
        if self.i:
            i = "%6i" % self.i
            if self.estimate: i += "/%6i" % self.estimate
            msg = "[%s] %s" % (i, msg)
        amcatlogging.debug(msg, level=logging.INFO,depth=depth, **kargs)
        
    def tick(self, msg = "", interval = None, depth=3, **kargs):
        """
        Indicate a single iteration

        Advance the iteration counter. If a whole number of intervals is reached,
        emit a message to the warning stream.

        @param msg: an optional message to add if the 'tick' is printed
        @param interval: if given, set the interval of this ticker
        """
        if interval: self.interval = interval
        self.i += 1
        if self.i % self.interval == 0:
            self._doTick(msg, depth, **kargs)

    def totaltime(self):
        """Print the total time so far to the warning stream"""
        self._doTick("Total time: %10f\n" % (time.time() - self.start))

def tickerate(seq, msg=None, getlen=True, useticker=None, detail=0):
    """
    Use a ticker to display progress while iterating over the given sequence

    For example,
    >>> for x in tickerate(seq): do(x)

    Is equivalent to:
    >>> for x in seq: do(x)

    Except for printing warning messages initially and  every N iterations.
    
    @param seq: the sequence to iterate over
    @param msg: an optional message to display initially
    @param getlen: unless False, use len(seq) as an C{estimate} for the ticker
    @param useticker: if given, use that ticker rather than the default L{ticker}()
    @param detail: optional C{detail} argument to pass to L{Ticker.warn}
    """
    fn, lineno, func = toolkit.getCaller()
    if msg is None: msg = "Starting iteration"
    if useticker is None: useticker = ticker()
    if getlen:
        if type(seq) not in (list, tuple, set):
            seq = list(seq)
        useticker.warn(msg, estimate=len(seq), detail=detail, fn=fn, lineno=lineno, func=func)
    else:
        useticker.warn(msg, fn=fn, lineno=lineno, func=func)
    for x in seq:
        useticker.tick(fn=fn, lineno=lineno, func=func)
        yield x

_SINGLETON = None
def ticker():
    """Return a default (singleton) ticker object"""
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = Ticker()
    return _SINGLETON

def warn(*args, **kargs):
    """Convenience method for ticker().warn(..)"""
    if 'depth' not in kargs: kargs['depth'] = 4
    ticker().warn(*args, **kargs)
def tick(*args, **kargs):
    """Convenience method for ticker().tick(..)"""
    if 'depth' not in kargs: kargs['depth'] = 4
    ticker().tick(*args, **kargs)

if __name__ == '__main__':
    for i in tickerate(range(100)):
        pass
