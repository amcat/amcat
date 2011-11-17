from __future__ import with_statement
import externalscripts, time

class TestScript(externalscripts.ExternalScriptBase):
    """Test Script that writes a message every second for 5 seconds with progress count"""

    scriptid=1 # how to avoid having to specify this?
    
    def invoke(self, db, data=None, msg=""):
        return super(TestScript, self).invoke(db, data, msg)
    def call(self, data=None, msg=""):
        return super(TestScript, self).call(data, msg)

    def _getOutputExtension(self, *args):
        return ".txt"
    
    def _run(self, data, out, err, msg):
        """Just write something every second for 5 seconds"""
        super(TestScript, self)._run(data, out, err, msg)
        out.write("Starting TestScript\n")
        with self.pm.monitored("sillytask", 100):
            for i in range(100):
                time.sleep(1)
                out.write("Iteration %i: %s\n" % (i, msg))
                self.pm.worked()
                #if i > 85: raise StandardError("O noes!")
        out.write("TestScript Done\n")
                

def test():
    """Call TestScript as external script and monitor progress until done"""
    import progress, dbtoolkit
    db = dbtoolkit.amcatDB()
    i = TestScript().invoke(db, msg="bla")
    db.commit()
    print "Monitoring invocation %i" % i.id
    while True:
        pm = i.getProgress()
        print pm
        if pm and pm.isDone(): break
        time.sleep(.5)
    print "done!\n----\n%s\n----" % open(out).read()

    
                
if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        import amcatlogging; amcatlogging.setup()
        print "NOT executing script, assuming this call is not from ExternalScript.call"
        test()
    else:
        TestScript().runFromCommand()
