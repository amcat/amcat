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
Test cases for amcat.tools
"""

from amcat.tools import amcattest
from amcat.tools import amcatlogging
import logging, StringIO

# TODO: this tester emits quite a lot of log messages.
#       Anyway to quiet them (in django test env)?
# TODO: the tests are sensitive to line numbers, which tend to
#       shift. Maybe use regexes?

class TestLogging(amcattest.PolicyTestCase):
    TARGET_MODULE=amcatlogging
    PYLINT_IGNORE_EXTRA= "W0703", 
    
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
        self.assertIn("test_amcatlogging.py:46", amcatlogging.format_records(s))

    def testException(self):
        with amcatlogging.collect() as s:
            try:
                x = 1/0
            except:
                logging.exception("Exception")
        self.assertIn('integer division or modulo by zero', amcatlogging.format_records(s))
        self.assertIn('tests/test_amcatlogging.py", line 54, in testException',
                      amcatlogging.format_records(s))
        with amcatlogging.collect() as s:
            with amcatlogging.logExceptions():
                raise Exception("!")
        self.assertEqual(len(s), 1)
        self.assertIn('tests/test_amcatlogging.py", line 62, in testException',
                      amcatlogging.format_records(s))
        
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
    amcattest.main()
