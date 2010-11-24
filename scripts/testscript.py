from __future__ import with_statement
import externalscripts, time

class TestScript(externalscripts.ExternalScriptBase):
    """Test Script that writes a message every second for 5 seconds with progress count"""
    
    def call(self, msg):
        return super(TestScript, self).call(None, msg)
        
    def _run(self, data, out, err, msg):
        """Just write something every second for 5 seconds"""
        super(TestScript, self)._run(data, out, err, msg)
        out.write("Starting TestScript\n")
        with self.pm.monitored("sillytask", 5):
            for i in range(5):
                time.sleep(1)
                out.write("Iteration %i: %s\n" % (i, msg))
                self.pm.worked()
                if i > 2: raise StandardError("O noes!")
        out.write("TestScript Done\n")
                

def test():
    """Call TestScript as external script and monitor progress until done"""
    import progress
    pid, out, err = TestScript().call("bla")
    
    print pid, out, err
    while True:
        pm = progress.readLog(open(err).read())
        print pm
        if pm and pm.isDone(): break
        time.sleep(.5)
    print "done!\n----\n%s\n----" % open(out).read()

    
                
if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        print "NOT executing script, assuming this call is not from ExternalScript.call"
        test()
    else:
        TestScript().runFromCommand()
