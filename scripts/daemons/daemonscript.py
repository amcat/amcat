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
Daemon Script that will run a specific action in an indefinite loop.
"""

import time, logging, tempfile, os.path

log = logging.getLogger(__name__)

from django import forms
from django import db

from amcat.contrib.daemon import Daemon
from amcat.scripts.script import Script
from amcat.tools import amcatlogging

ACTIONS = [('start', 'Start the Daemon'), ('stop', 'Stop the Daemon'),
           ('restart', 'Restart the Daemon'), ('test', 'Test the Daemon')]

class StopDeamon(Exception):
    """Signals that the daemon should stop running"""

class DaemonForm(forms.Form):
    """Form for scrapers"""
    action = forms.ChoiceField(choices=ACTIONS)


class DaemonScript(Script):
    options_form=DaemonForm

    def run(self, input=None):
        """
        Script entry point
        """
        self.input = input
        action = self.options['action']
        if action == 'test':
            self.test()
        else:
            # set up daemon
            self._setup_logging()
            pidfile = self._get_filename(".pid")
            self.d = Daemon(self.run_daemon, pidfile)
            # run the start/stop/restart method
            getattr(self.d, action)()


    def run_daemon(self):
        """
        Main daemon function. Tries to call run_action indefinitely, with 
        sleep in between failures or False exit values.
        """
        self.prepare()
        log.info("{} started".format(self.__class__.__name__))
        while True:
            try:
                result = self.run_action()
                if not result:
                    log.info('No results found, sleeping for 5 seconds')
                    time.sleep(5)
            except StopDeamon:
                log.exception('StopDaemon received, quitting')
                try:
                    d.delpid()
                except Exception as e:
                    log.exception('Exception on deleting pid: %s' % e)
                break
            except db.DatabaseError:
                log.exception('Database error received. Attempting to reset connection..')

                try:
                    db.connection.connection.close()
                except:
                    # Connection already closed. Ignore exception.
                    pass

                db.connection.connection = None

                time.sleep(30)
            except:
                log.exception('While loop exception, sleeping for 10 seconds')
                time.sleep(10)

            # Reset db-queries to prevent memory-leaking
            db.reset_queries()

    def prepare(self):
        """
        Hook to allow a subclass to run actions prior to running. This will be called in the forked process
        before the main loop is run
        """

    def run_action(self):
        """
        Do the actual work.
        @return: boolean. If False (or None!), the daemon will sleep a minute before retrying
        """
        raise NotImplementedError

    def test(self):
        """
        Function to be called for action 'test'.
        Default sets up stderr logging and calls run_action once
        """
        self.prepare()
        self.run_action()
                
    def _get_filename(self, suffix="log"):
        """
        Get the filename, eg for the pid and logging. Default uses a file in the temp 
        directory named after the classname in all lowercase.
        """
        return os.path.join(tempfile.gettempdir(),
                            self.__class__.__name__.lower() + suffix)

    def _setup_logging(self):
        """
        Set up the logging facility. By default runs a file handler in _get_filename(".log")
        """
        fn = self._get_filename(".log")
        amcatlogging.setFileHandler(fn)
        amcatlogging.info_module()
        amcatlogging.debug_module('amcat.tools.amcatsolr')




###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestDaemon(amcattest.PolicyTestCase):
    def test_test(self):
        class _TestDaemon(DaemonScript):
            def run_action(self):
                l[0]+=1
        l = [0]
        _TestDaemon(action='test').run()
        self.assertEqual(l, [1])
        
if __name__ == "__main__":
    from amcat.scripts.tools import cli
    cli.run_cli()
    
