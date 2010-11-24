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

"""Base module for Scripts to be run as separate processes

External Scripts are scripts that are supposed to be run as background
processes, e.g. for creating a Lucene index or for preparing an SPSS
export file. 

The ExternalScript and Invocation classes are Cachables representing the
externalscripts and _invocations tables, respectively. They can be used
to easily acquire the concrete base object and monitor progress.

The L{ExternalScriptBase} from this module should not be used
directly, but concrete script will inherit from this class. In
principle, there are three use cases for subclasses of
ExternalScriptBase:

1) a _caller_ will use the object to find out which arguments are
  needed and to start the background process using
  L{ExternalScript.call}, after which it can make an entry in the
  externalscripts_invocations table if desired.
2) the _process_ called from the command line will do the actual work,
  generally by running L{ExternalScript.runFromCommand}, which parses
  the arguments and calls L{ExternalScript._run}.
3) a _monitor_ can use the object to interpret the output and error
  streams of the process, possibly based on the
  externalscripts_invocations table
"""

import logging; log = logging.getLogger(__name__)
import toolkit, subprocess, inspect, sys, idlabel, user
import progress
from cachable2 import Cachable, DBProperty, ForeignKey, DBProperties

class ExternalScript(Cachable):
    __table__ = 'externalscripts'
    __idcolumn__ = 'scriptid'

    modulename, classname = DBProperties(2)

    def getInstance(self):
        mod = __import__(self.modulename, fromlist=self.classname)
        cls = getattr(mod, self.classname)
        return cls()

def getScript(db, scriptid):
    return ExternalScript(db, scriptid).getInstance()

class Invocation(Cachable):
    __table__ = 'externalscripts_invocations'
    __idcolumn__ = 'invocationid'

    script = DBProperty(ExternalScript)
    user = DBProperty(user.User)
    insertdate, outfile, errfile, argstr, pid = DBProperties(5)

    def getScript(self):
        return self.script.getInstance()
    def getProgress(self):
        log = open(self.errfile)
        return self.script.getInstance().interpretStatus(log)


class ExternalScriptBase(object):
    """Class that represents an external script such as a codingjob extraction script"""

    def __init__(self, command=None):
        """
        @param filename: name of the command, defaults to 'python /path/modulename.py'
        """
        self.command = command 

    def call(self, data=None, *args, **kargs):
        """Call this script as an external process

        @param data: optional data to send to script
        @param args: 'command line' arguments for script
        @param kargs: 'outfile' and 'errfile' str filenames for input and output
        @return: tuple of (pid, outfilename, errfilename)
        """
        cmd = self._getCommand(*args)
        if 'outfile' in kargs:
            out = kargs['outfile']
        else:
            out = toolkit.tempfilename(prefix="tmp-script-", suffix=".out")
        if 'errfile' in kargs:
            err = kargs['errfile']
        else:
            err = toolkit.tempfilename(prefix="tmp-script-", suffix=".err")

        log.info("Calling %s >%s 2>%s" % (cmd, out, err))

        p = subprocess.Popen(cmd, stdout=open(out,"w"), stderr=open(err,"w"), stdin=subprocess.PIPE)

        if data:
            if not toolkit.isIterable(data, excludeStrings=True):
                data = [data]
            for row in data:
                p.stdin.write(self._serialise(row))
                p.stdin.write("\n")
        p.stdin.close()

        return p.pid, out, err

    def interpretStatus(self, errstream):
        """Interpret the err stream of the process

        @return: a L{progress.ProgressMonitor} object
        """
        return progress.readLog(errstream.read(), monitorname=self.__class__.__name__)

    def _serialise(self, obj):
        """Helper function to serialise an argument or data line to a str"""
        if isinstance(obj, idlabel.IDLabel): obj = obj.id
        return str(obj)
        
    def _getCommand(self, *args):
        """Return the command array (e.g. to be used for Popen)"""
        if self.command:
            if type(self.command) in (str, unicode):
                cmd = [self.command]
            else:
                cmd = list(self.command)
        else:
            cmd = ["python", inspect.getfile(self.__class__)]
        for arg in args:
            cmd += [self._serialise(arg)]
        return cmd
    
    def _parseArgs(self, *args):
        """Parse the command line args for use by L{_run}
        
        @param args: a sequence of strings from the command line args
        @return: a sequence of objects to be used by run
        """
        return args           
    
    def _run(self, data, out, err, *args):
        """Run the actual script. Subclasses should override
        
        @param data: the stream for the data input
        @param out: the output stream to use, which should be interpretable
          as stated by L{getOutputType}
        @param err: the error stream to use
        @param args: the arguments as parsed by _parseArgs
        """
        import amcatlogging
        amcatlogging.setStreamHandler(err)
        amcatlogging.infoModule()
        self.pm = progress.ProgressMonitor(self.__class__.__name__)
        self.pm.listeners.add(progress.TickLogListener(log, 20))
    
    def runFromCommand(self):
        """Parse the command line arguments and L{_run} the script"""
        args = self._parseArgs(*sys.argv[1:])
        self._run(sys.stdin, sys.stdout, sys.stderr, *args)
        
if __name__ == '__main__':
    import amcatlogging; amcatlogging.setup()
    ExternalScript().call()
