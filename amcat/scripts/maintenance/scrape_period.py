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
Script to run a scraper at given date range
"""

from amcat.scripts.script import Script
from amcat.scraping.scraper import ScraperForm
from amcat.models.scraper import Scraper
from amcat.scripts.maintenance.deduplicate import DeduplicateScript
from amcat.scraping.controller import RobustController

from django import forms
from datetime import date, timedelta

import logging;log = logging.getLogger(__name__)

class PeriodScraperForm(ScraperForm):
    first_date = forms.DateField()
    last_date = forms.DateField(required=False)

    scraper_id = forms.ModelChoiceField(queryset = Scraper.objects.all(), required = False)
    scraper_module = forms.CharField(required = False)
    scraper_classname = forms.CharField(required = False)
    scraper_username = forms.CharField(required = False)
    scraper_password = forms.CharField(required = False)

    deduplicate = forms.BooleanField(required = False)


class PeriodScraper(Script):
    options_form = PeriodScraperForm

    def get_scraper(self, date):
        scraper_options = {
            'date' : date,
            'project' : self.options['project'].id,
            'articleset' : self.options['articleset'].id,
            'username' : self.options['scraper_username'],
            'password' : self.options['scraper_password']
            }

        if self.options['scraper_id']:
    
            scraper_model = Scraper.objects.get(pk = self.options['scraper_id'].id)
            if scraper_model.username:
                scraper_options['username'] = scraper_model.username
                scraper_options['password'] = scraper_model.password
            return scraper_model.get_scraper(**scraper_options)

        elif self.options['scraper_module'] and self.options['scraper_classname']:

            scraper_module = __import__(
                self.options['scraper_module'],
                fromlist = self.options['scraper_classname'])
            scraper_class = getattr(scraper_module, self.options['scraper_classname'])

            return scraper_class(**scraper_options)

        else:
            raise ValueError("please submit either scraper_id or both scraper_module and scraper_classname")


    def run(self, _input):
        if not self.options['last_date']:
            self.options['last_date'] = date.today()

        if self.options['deduplicate']:
            dedu = True
        else:
            dedu = False

        n_days = (self.options['last_date'] - self.options['first_date']).days
        days = [self.options['first_date'] + timedelta(days = x) for x in range(n_days + 1)]
        scrapers = [self.get_scraper(d) for d in days]
        RobustController().scrape(scrapers, deduplicate = dedu)




if __name__ == "__main__":
    from amcat.scripts.tools import cli
    cli.run_cli(PeriodScraper)
