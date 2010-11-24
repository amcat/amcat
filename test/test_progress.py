import amcattest, progress

class TestProgress(amcattest.AmcatTestCase):

    def testState(self):
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

if __name__ == '__main__':
    amcattest.main()
        
