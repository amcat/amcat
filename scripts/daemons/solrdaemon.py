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
Daemon that checks if there are any Articles on the queue
and indexes them with Solr.
"""
import time, sys, logging, argparse
log = logging.getLogger(__name__)

from django.db import transaction

from amcat.contrib.daemon import Daemon
from amcat.tools.amcatsolr import index_articles_from_db
from amcat.tools.multithread import distribute_tasks
from amcat.models.article_solr import SolrArticle

class SolrDeamon(Daemon):
    
    def run(self):
        """
            Main daemon function.
            First it checks for any articles in the queue, 
            if found it calls the solr indexer and removes the items from the queue
            Else it continues sleeping
        """
        log.info("SOLRDaemon started")
        while True:
            try:
                result = self.run_action()
                if not result:
                    log.info('No results found, sleeping for 1 minute')
                    time.sleep(60)
                    
            except:
                log.error('while loop exception, sleeping for 1 minute', exc_info=True)
                time.sleep(60)

    def run_action(self):
        return index_articles_from_db(nthreads=1)

    def test(self):
        from amcat.tools import amcatlogging
        amcatlogging.setup()
        self.run_action()
                
    
if __name__ == "__main__":
    from amcat.tools import amcatlogging
    amcatlogging.setFileHandler("solrdaemon.log")
    amcatlogging.info_module()
    amcatlogging.debug_module('amcat.tools.amcatsolr')
    daemon = SolrDeamon('/tmp/solr-daemon.pid')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['test', 'start', 'stop', 'restart'],
                   help='Control the SOLR Daemon')
    args = parser.parse_args()
    # get action corresponding to start/stop/restart and execute it
    action = getattr(SolrDeamon, args.command)
    action(daemon)
    
