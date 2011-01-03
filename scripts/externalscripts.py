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
  L{ExternalScript.call} or L{externalscript.invoke}.
2) the _process_ called from the command line will do the actual work,
  by running this module with the RUN paramter, which calls
  L{ExternalScriptBase.runFromCommand} on the script object.
3) a _monitor_ can use the object to interpret the output and error
  streams of the process, possibly based on the externalscripts_invocations table

For implementing an externalscript, subclass from ExternalScriptBase and override
the _run method, and add the script to the externalscripts database table.

To call an externalscript, create the ExternalScript domain object, and use
call() or invoke() with the appropriate commands.

To monitor an externalscript in a separate process, obtain the Invocation object
(through ID or as the result of calling invoke()) and call getProgresss()

The best way to run externalscripts from the command line, either in-process
or in a new process, is through calling this script.

Usage:

python externalscripts.py COMMAND SCRIPTID [ARGS] [<DATA]

Where COMMAND is one of:
INVOKE: call the script and add a database invocation entry
CALL: call the script as an external command (using RUN), printing pid, out, and err
RUN: run the script directly 

Where SCRIPTID is the id of the script to call, and args and data are
passed to the script as normal.

for CALL and INVOKE, the script can use the ARGS and DATA
"""

import logging; log = logging.getLogger(__name__)
import toolkit, subprocess, inspect, sys, idlabel, user
import progress
from cachable2 import Cachable, DBProperty, ForeignKey, DBProperties

def _getClass(modulename, classname):
    """Import the module and return the class contained in it

    Apache users should supply an apache-aware importer"""
    mod = __import__(modulename, fromlist=classname)
    return getattr(mod, classname)

IMPORT_SCRIPT = _getClass


class ExternalScript(Cachable):
    __table__ = 'externalscripts'
    __idcolumn__ = 'scriptid'

    modulename, classname, label, category = DBProperties(4)

    def getInstance(self):
        cls = IMPORT_SCRIPT(self.modulename, self.classname)
        return cls()

    def _getCommand(self, script, args):
        return ["python",__file__, "RUN", str(self.id)] + [script._serialise(arg) for arg in args]
    
    def invoke(self, db, data, *args, **kargs):
        """Call this script and  store and return an Invocation"""
        script = self.getInstance()
        cmd = self._getCommand(script, args)
        pid, out, err = self.call(data, *args, **kargs)
        return Invocation.create(db, script=self.id, outfile=out, errfile=err, pid=pid,
                                 argstr=" ".join(cmd), outputtype=script._getOutputType(*args))
                

    def call(self, data=None, *args, **kargs):
        """Call the referenced script as an external process through this module's __main__

        @param data: optional data to send to script
        @param args: 'command line' arguments for script
        @param kargs: 'outfile' and 'errfile' str filenames for input and output
        @return: tuple of (pid, outfilename, errfilename)
        """
        script = self.getInstance()
        cmd = self._getCommand(script, args)
        log.debug("Calling %s with data=%r, args=%r, cmd=\n%s" % (script, data, args, cmd))
        
        
        out = (kargs['outfile'] if 'outfile' in kargs 
               else toolkit.tempfilename(prefix="tmp-script-", suffix=script._getOutputExtension(*args)))
        
        err = (kargs['errfile'] if 'errfile' in kargs 
               else toolkit.tempfilename(prefix="tmp-script-", suffix=".err"))

        log.info("Calling %s >%s 2>%s" % (cmd, out, err))

        p = subprocess.Popen(cmd, stdout=open(out,"w"), stderr=open(err,"w"), stdin=subprocess.PIPE)

        if data:
            if not toolkit.isIterable(data, excludeStrings=True):
                data = [data]
            for row in data:
                p.stdin.write(script._serialise(row))
                p.stdin.write("\n")
        p.stdin.close()

        return p.pid, out, err

    
def getExternalScripts(db, category):
    for es in ExternalScript.all(db):
        if es.category == category:
            yield es
    
def getScript(db, scriptid):
    return ExternalScript(db, scriptid).getInstance()

class Invocation(Cachable):
    __table__ = 'externalscripts_invocations'
    __idcolumn__ = 'invocationid'
    __labelprop__ = 'argstr'

    script = DBProperty(ExternalScript)
    user = DBProperty(user.User)
    insertdate, outfile, errfile, argstr, pid, outputtype = DBProperties(6)

    def getScript(self, **kargs):
        return self.script.getInstance(**kargs)
    def getProgress(self, **kargs):
        log = open(self.errfile)
        try:
            pm =  self.script.getInstance(**kargs).interpretStatus(log)
            if not pm: raise TypeError("Could not interpret log file")
        except Exception, e:
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            pm = progress.ProgressMonitor()
            pm.error(e, exc_traceback)
        return pm


class ExternalScriptBase(object):
    """Class that represents an external script such as a codingjob extraction script"""

    def interpretStatus(self, errstream):
        """Interpret the err stream of the process

        @return: a L{progress.ProgressMonitor} object
        """
        return progress.readLog(errstream.read(), monitorname=self.__class__.__name__)

    def _serialise(self, obj):
        """Helper function to serialise an argument or data line to a str"""
        log.debug("Serialising obj=%s" % (obj,))
        if isinstance(obj, idlabel.IDLabel): obj = obj.id
        log.debug("Serialised to %r" % str(obj))
        return str(obj)

    def _getOutputType(self, *args):
        """How to interpret the output file, i.e. return its (mime) type"""
        return "text/plain"
    def _getOutputExtension(self, *args):
        """Suggest an extension for the output file"""
        return ".out"
    
    def _serialiseArgs(self, *args):
        """Return the command array (e.g. to be used for Popen)"""
        if self.command:
            if type(self.command) in (str, unicode):
                cmd = [self.command]
            else:
                cmd = list(self.command)
        else:
            file = self.__class__.__file__
            cmd = ["python", file]
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
        """Run the actual script. Subclasses should override and may call this base for logging
        
        @param data: the stream for the data input
        @param out: the output stream to use, which should be interpretable
          as stated by L{getOutputType}
        @param err: the error stream to use
        @param args: the arguments as parsed by _parseArgs
        """
        self.out = out
        import amcatlogging
        amcatlogging.setStreamHandler(err)
        amcatlogging.infoModule()
        self.pm = progress.ProgressMonitor(self.__class__.__name__)
        self.pm.listeners.add(progress.TickLogListener(log, 100))
    
    def runFromCommand(self, args=None):
        """Parse the command line arguments and L{_run} the script"""
        if args is None: args = sys.argv[1:]
        args = self._parseArgs(*args)
        log.debug("Running %s with args=%s" % (self, args))
        self._run(sys.stdin, sys.stdout, sys.stderr, *args)

import amcatlogging; amcatlogging.debugModule()
        
if __name__ == '__main__':    

    import sys
    if len(sys.argv) < 3:
        print >>sys.stderr, __doc__
        sys.exit()

    cmd = sys.argv[1].lower()
    scriptid = int(sys.argv[2])
    args = sys.argv[3:]

    # get externalscript instance
    import dbtoolkit
    db = dbtoolkit.amcatDB(use_app=True)
    script = ExternalScript(db, scriptid)

    if cmd == "call":
        import amcatlogging; amcatlogging.setup()
        print script.call(sys.stdin.read(), *args)
    elif cmd == "invoke":
        import amcatlogging; amcatlogging.setup()
        inv = script.invoke(db, sys.stdin.read(), *args)
        db.commit()
        print "Created invocation %i" % inv.id
    elif cmd == "run":
        es = script.getInstance()
        log.debug("calling runFromCommand(%s)" % args)

        es.runFromCommand(args)
    else:
        print >>sys.stderr, __doc__
        sys.exit()

