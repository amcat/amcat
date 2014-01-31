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
Script to update the index after scraping
"""

from amcat.scripts.script import Script
from amcat.models.articleset import ArticleSet
from amcat.models.scraper import Scraper

class UpdateIndexScript(Script):
    def run(self, _input = None):
        setids = Scraper.objects.filter(active = True).values('articleset')
        for s in ArticleSet.objects.filter(pk__in = setids):
            s.refresh_index()

if __name__ == "__main__":
    from amcat.scripts.tools import cli
    cli.run_cli(UpdateIndexScript)
        
