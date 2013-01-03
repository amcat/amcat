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
Daemon that checks if there are any dirty article sets that need to be
queried and adds them to Solr
"""

from django.db import transaction

from amcat.scripts.daemons.daemonscript import DaemonScript

from amcat.models import ArticleSet
from amcat.tools import amcatsolr

import logging
log = logging.getLogger(__name__)

class IndexDaemon(DaemonScript):
    def run_action(self):
        try:
            with transaction.commit_on_success():
                aset = ArticleSet.objects.filter(indexed=True, index_dirty=True)[0]
        except IndexError:
            log.debug("No dirty sets found, skipping")
            return

        log.debug("Refreshing index for set: {aset.id} : {aset}".format(**locals()))
        with transaction.commit_on_success():
            aset.refresh_index()
        return aset

if __name__ == '__main__':
    from amcat.tools import amcatlogging
    amcatlogging.debug_module()
    amcatlogging.debug_module("amcat.models.articleset")
    from amcat.scripts.tools.cli import run_cli
    run_cli()
