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
Daemon that checks if there are any Articles on the analysis_articlesets_queue
and adjusts the analysis_queue table as necessary
"""
from django.db import transaction

from amcat.scripts.daemons.daemonscript import DaemonScript

from amcat.models.analysis import AnalysisQueue, AnalysisArticleSetQueue, add_to_queue
from amcat.nlp.preprocessing import set_preprocessing_actions

import logging; log = logging.getLogger(__name__)

BATCH = 5

class PreprocessingArticleSetsDaemon(DaemonScript):

    @transaction.commit_on_success
    def run_action(self):
        # Retrieve top sets
        asets = [a.articleset for a in AnalysisArticleSetQueue.objects.all()[:BATCH]]
        log.info("Adding {} sets to queue".format(len(asets)))

        # Add articles in articlesets to article queue
        for aset in asets:
            add_to_queue(*(a.id for a in aset.articles.all().only("id")))

        # Clean up articleset queue
        AnalysisArticleSetQueue.objects.filter(
            articleset__id__in=[a.id for a in asets]
        ).delete()

        return asets

if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli()
