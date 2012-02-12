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
import time, sys, logging

from django.db import transaction

from amcat.contrib.daemon import Daemon
from amcat.scripts.daemons.index_solr_articles import index_articles
from amcat.model.article_solr import SolrArticle
from amcat.model.article import Article

# temporary file handler, for debug purposes
formatter = logging.Formatter(
	'[%(asctime)-6s %(name)s %(levelname)s] %(message)s')
fileLogger = logging.handlers.RotatingFileHandler(filename='/tmp/solrdeamon.log',
                                                  maxBytes = 1024*1024*5, backupCount = 3)
fileLogger.setLevel(logging.DEBUG)
fileLogger.setFormatter(formatter)
logging.getLogger('').addHandler(fileLogger)

log = logging.getLogger(__name__)

 
class SolrDeamon(Daemon):
    
    @transaction.commit_manually
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
                solrArticles = SolrArticle.objects.filter(started=False)[:10000]
                solrArticleIds = [sa.id for sa in solrArticles]
                 # we need a new queryset since after slicing update() is no longer allowed by Django..
                solrArticlesQueryset = SolrArticle.objects.filter(pk__in=solrArticleIds)
                if solrArticles.count() == 0:
                    log.debug('going to sleep')
                    time.sleep(5)
                solrArticlesQueryset.update(started=True)
                    
                index_articles(Article.objects.filter(pk__in=solrArticles.values_list('article', flat=True))) 
                    
                solrArticlesQueryset.delete()
            except:
                log.exception('while loop exception')
                time.sleep(60)
                
            

    
if __name__ == "__main__":
    daemon = SolrDeamon('/tmp/solr-daemon.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
