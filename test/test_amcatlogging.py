from __future__ import with_statement
import unittest, amcattest, amcatlogging, logging, StringIO

class TestLogging(amcattest.AmcatTestCase, logging.Filter):

    def setUp(self):
        self.logs = []
    
    def filter(self, logrecord):
        self.logs.append(logrecord)
        return True
    
    def testLog(self):
        
        l = amcatlogging.getLogger()
        l.addFilter(self)
        try:
            amcatlogging.info("testmessage")
            self.assertEqual(self.logs[-1].msg, "testmessage")
            
            amcatlogging.getLogger("amcat_unittest")
            amcatlogging.info("testmessage2")
            self.assertEqual(self.logs[-1].application, "amcat_unittest")
        finally:
            l.removeFilter(self)

    def testContext(self): 
        amcatlogging.getLogger("amcat_unittest")
        with amcatlogging.collect() as s:
            amcatlogging.info("debug message")
            amcatlogging.info("debug message")
        self.assertEqual(2, len(s))
        self.assertIn("test_amcatlogging.py:30 amcat_unittest", amcatlogging.format(s))

    def testException(self):
        with amcatlogging.collect() as s:
            try:
                x = 1/0
            except:
                amcatlogging.exception()
        self.assertIn('integer division or modulo by zero\n', amcatlogging.format(s))
        self.assertIn('test/test_amcatlogging.py", line 38, in testException', amcatlogging.format(s))
        with amcatlogging.collect() as s:
            with amcatlogging.logExceptions():
                x = 1/0
        self.assertEqual(len(s), 1)
        self.assertIn('test/test_amcatlogging.py", line 45, in testException',amcatlogging.format(s))
        
        
if __name__ == '__main__':
    unittest.main()
