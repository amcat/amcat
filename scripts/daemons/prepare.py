#! /usr/bin/python
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
Daemon that checks if preprocessors need to be prepared first and does the
preparation (eg sentence splitting)
"""
from amcat.models import ArticleAnalysis

from amcat.scripts.daemons.daemonscript import DaemonScript

import logging;
from amcat.models.analysis import Analysis

log = logging.getLogger(__name__)

BATCH = 1000

class PrepareDaemon(DaemonScript):

    def prepare(self):
        self.analyses = dict(get_analyses())

    def run_action(self):
        for a, s in self.analyses.items():
            log.info("Checking for articles to prepare for analysis: {a}".format(**locals()))
            articles = ArticleAnalysis.objects.filter(analysis=a, prepared=False)[:100]
            s.prepare_articles(articles)



def get_analyses():
    for a in Analysis.objects.filter(plugin__active=True):
        s = a.get_script()
        if s.needs_preparation:
            yield a, s



if __name__ == "__main__":
    from amcat.scripts.tools.cli import run_cli
    run_cli()