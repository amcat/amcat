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
Script to be run daily for data input (scraping, preprocessing etc.
"""

from datetime import date, timedelta

from django import forms

from amcat.scripts.script import Script
from amcat.scripts.tools import cli
import amcat.scripts.forms

from amcat.scraping.scraper import DateForm, MultiScraper
from amcat.scraping.controller import SimpleController
from amcat.models.scraper import get_scrapers


class DailyScript(Script):
    options_form = DateForm

    def run(self, _input):
        date = self.options['date']
        project = self.options['projectid']
        
        scrapers = list(get_scrapers(date=date, projectid=project.id))
        m = MultiScraper(scrapers)

        c = SimpleController()
        c.scrape(m)
        

        
if __name__ == '__main__':
    cli.run_cli(DailyScript)
