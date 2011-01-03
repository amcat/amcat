from __future__ import with_statement
import unittest, amcattest, amcatlogging, logging, StringIO

class TestLogging(amcattest.AmcatTestCase, logging.Filter):

    def setUp(self):
        self.logs = []

    def filter(self, logrecord):
        self.logs.append(logrecord)
        return True
    
    def testCollect(self): 
        with amcatlogging.collect() as s:
            logging.info("debug message")
            logging.info("debug message")
        self.assertEqual(2, len(s))
        self.assertIn("test_amcatlogging.py:15", amcatlogging.format(s))

    def testException(self):
        with amcatlogging.collect() as s:
            try:
                x = 1/0
            except:
                logging.exception("Exception")
        self.assertIn('integer division or modulo by zero', amcatlogging.format(s))
        self.assertIn('test/test_amcatlogging.py", line 23, in testException', amcatlogging.format(s))
        with amcatlogging.collect() as s:
            with amcatlogging.logExceptions():
                raise Exception("!")
        self.assertEqual(len(s), 1)
        self.assertIn('test/test_amcatlogging.py", line 30, in testException',amcatlogging.format(s))
        
    def testModuleLevel(self):
        log = logging.getLogger(__name__)
        log.addFilter(amcatlogging.ModuleLevelFilter())
        amcatlogging.infoModule()
        with amcatlogging.collect() as s:
            log.debug("debug message")
            log.info("info message")
            log.warn("warn message")
        self.assertEqual(len(s), 2)
        amcatlogging.debugModule()
        with amcatlogging.collect() as s:
            log.debug("debug message")
            log.info("info message")
            log.warn("warn message")
        self.assertEqual(len(s), 3)
            
        
if __name__ == '__main__':
    unittest.main()
