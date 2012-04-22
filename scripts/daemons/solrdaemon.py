#!/usr/bin/python
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

# todo this could be generalized to run an arbitrary analysis

import logging
log = logging.getLogger(__name__)

from amcat.scripts.daemons.daemonscript import DaemonScript
from amcat.models.analysis import Analysis, AnalysisArticle

BATCH = 10000

class SolrDeamon(DaemonScript):
    """
    The SolrDaemon checks whether there are articles that need to be updated
    and updates them
    """

    def run_daemon(self):
        from amcat.nlp.solr import Solr
        self.script = Solr(Analysis.objects.get(plugin=Solr.get_plugin()))
        super(SolrDeamon, self).run_daemon()

    def run_action(self):
        log.debug("Running analysis for %s : %s" % (self.script, self.script.analysis))
        articles = AnalysisArticle.objects.filter(analysis=self.script.analysis)
        # add articles
        to_add = list(articles.filter(done=False, delete=False)[:BATCH])
        if to_add:
            self.script.add_articles([a.article_id for a in to_add])
            log.info("Setting done=True on %i articles" % len(to_add))
            AnalysisArticle.objects.filter(pk__in=(a.id for a in to_add)).update(done=True)
        # remove articles
        to_delete = list(articles.filter(delete=True)[:BATCH])
        if to_delete:
            self.script.delete_articles([a.article_id for a in to_delete])
            log.info("Removing %i articles from analysis" % len(to_delete))
            AnalysisArticle.objects.filter(pk__in=(a.id for a in to_delete)).delete()
        
        
        

if __name__ == "__main__":
    from amcat.tools import amcatlogging
    amcatlogging.debug_module()
    from amcat.scripts.tools.cli import run_cli
    run_cli()
