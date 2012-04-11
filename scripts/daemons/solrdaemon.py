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
from amcat.tools.multithread import distribute_tasks
from amcat.nlp.solr import Solr
from amcat.tools.amcatsolr import index_articles, delete_articles
from amcat.models.analysis import Analysis
from amcat.models.article_preprocessing import ArticleAnalysis

BATCH = 10000

class SolrDeamon(DaemonScript):
    """
    The SolrDaemon checks whether there are articles that need to be updated
    and updates them
    """

    def __init__(self, *args, **kargs):
        super(SolrDeamon, self).__init__(*args, **kargs)
        self.analysis = Analysis.objects.get(plugin__module=Solr.__module__,
                                             plugin__class_name=Solr.__name__)
    def run_action(self):
        # add articles
        q = ArticleAnalysis.objects.filter(analysis=self.analysis, done=False, delete=False)
        q = q.select_related("article")
        aas = list(q[:BATCH])
        log.info("aas: %r" % aas)
        index_articles([aa.article for aa in aas])
        log.info("Setting done=True on %i articles" % len(aas))
        ArticleAnalysis.objects.filter(pk__in=(aa.id for aa in aas)).update(done=True)

if __name__ == "__main__":
    from amcat.tools import amcatlogging
    amcatlogging.debug_module("amcat.tools.amcatsolr")
    from amcat.scripts.tools.cli import run_cli
    run_cli()
