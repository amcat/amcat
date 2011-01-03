from __future__ import with_statement
import amcattest, progress, amcatlogging

class TestProgress(amcattest.AmcatTestCase):

    def testState(self):
        """Check whether the state logic is correct"""
        m = progress.ProgressMonitor()
        self.assertRaises(progress.IllegalMonitorStateException, m.worked)
        self.assertRaises(progress.IllegalMonitorStateException, m.done)
        m.start()
        self.assertRaises(progress.IllegalMonitorStateException, m.start)
        m.worked(50)
        self.assertEqual(.5, m.percentDone())
        m.done()
        self.assertRaises(progress.IllegalMonitorStateException, m.start)
        self.assertRaises(progress.IllegalMonitorStateException, m.worked)
        m.error(StandardError("!"))
        self.assertRaises(progress.IllegalMonitorStateException, m.done)
        self.assertRaises(progress.IllegalMonitorStateException, m.start)
        self.assertRaises(progress.IllegalMonitorStateException, m.worked)
        

    def testError(self):
        """Test whether raising an error on a monitored process is handled"""
        purposeful_error = StandardError("bla!")
        with progress.monitored("test", 100) as mon:
            self.assertEqual(mon.state, progress.STATE_STARTED)
            mon.worked(10)            
            raise purposeful_error
        self.assertEqual(mon.exception,  purposeful_error)
        self.assertEqual(mon.progress, 10)
        self.assertEqual(mon.state, progress.STATE_ERROR)
        self.assertRaises(StandardError, mon.checkError)

        mon = progress.ProgressMonitor("main")
        with mon.monitored("test", 100):
            self.assertEqual(mon.state, progress.STATE_STARTED)
            mon.worked(10)            
            raise purposeful_error
        self.assertEqual(mon.name, "main")
        self.assertEqual(mon.exception,  purposeful_error)
        self.assertEqual(mon.progress, 10)
        self.assertEqual(mon.state, progress.STATE_ERROR)
        self.assertRaises(StandardError, mon.checkError)

    def testReadLog(self):
        """Test whether the readLog function can correctly interpret log files"""
        import logging;log =logging.getLogger("IGNORE")
        p = progress.ProgressMonitor("main")
        p.listeners.add(progress.TickLogListener(log, 5))
        with amcatlogging.collect() as logentries:
            p.start("taskname")
            for i in range(40):
                p.worked()
            for i in progress.tickerate(range(100), monitor=p, log=log, monitorname="sub", submonitorwork=60):
                if i > 50: break
        logstr = "\n".join(map(amcatlogging.format, logentries))
        l = progress.readLog(logstr, "main")
        l2 = progress.readLog(logstr, "sub")
        l3 = progress.readLog(logstr, taskname="Iteration")
        for (pm, name, tname, percent, state) in [
            (l, "main", "taskname", .6, progress.STATE_STARTED),
            (l2, "sub", "Iteration", .5, progress.STATE_STARTED),
            (l3, "sub", "Iteration", .5, progress.STATE_STARTED),
            ]:

            self.assertEqual(pm.name, name)
            self.assertEqual(pm.taskname, tname)
            self.assertEqual(pm.percentDone(), percent)
            self.assertEqual(pm.state, state)
            
if __name__ == '__main__':
    amcattest.main()
        
