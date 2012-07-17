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
This deamon checks if there are any Articles in analysis_articles. If there
are, it runs the plugins associated with them.
"""

from django.db import transaction

from amcat.scripts.daemons.daemonscript import DaemonScript
from amcat.models.analysis import AnalysisArticle

from collections import defaultdict

BATCH = 1000

import logging; log = logging.getLogger(__name__)

class AnalysisDaemon(DaemonScript):
    def _to_plugin_dict(self, analysis_arts):
        res = defaultdict(set)

        for aa in analysis_arts:
            res[aa.analysis.plugin].add(aa)

        return res

    @transaction.commit_on_success
    def run_action(self):
        """
        Analyse all articles.
        
        TODO: If analysis.sentences is True, also analyse all sentences.
        """
        arts = AnalysisArticle.objects.filter(
            analysis__plugin__active=True, started=False
        ).select_related("analysis__plugin")[:BATCH]

        # We can't use update() on sliced queries. Workaround:
        arts = AnalysisArticle.objects.filter(
            id__in=[a.id for a in arts]
        )

        # Indicate that we started analysing
        arts.update(started=True)

        for plugin, aarts in self._to_plugin_dict(arts).items():
            script = plugin.get_instance()
            script.run(aarts)

        # Indicate that we're done analysing
        arts.update(done=True)

        return arts

if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli()
