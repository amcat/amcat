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
Script add a codebook
"""

import logging; log = logging.getLogger(__name__)
from amcat.scripts.script import Script

from amcat.models import Project

class CacheProjectMediums(Script):
    def run(self, _input=None):
        # Don't query database to find out how many projects we have, since
        # we'll already have to fetch all projects.
        projects = Project.objects.only("id")

        for i, project in enumerate(projects, start=1):
            log.info("Warming cache for project {project.id} [{i}/{}]".format(len(projects), **locals()))
            project.cache_mediums()

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestCacheProjectMediums(amcattest.PolicyTestCase):
    def test_caching(self):
        aset = amcattest.create_test_set(1)
        CacheProjectMediums().run()

        with self.checkMaxQueries(1, "Get cached project mediums"):
            list(aset.project.get_mediums())

