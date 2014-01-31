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

from datetime import timedelta
from django import forms

from amcat.models.scraper import Scraper
from amcat.scripts.script import Script
from amcat.scripts.actions.deduplicate import Deduplicate


class Options(forms.Form):
    first_date = forms.DateField()
    last_date = forms.DateField()

class FixGapsScript(Script):
    options_form = Options
    def run(self, _input = None):
        to_run = []
        for date in self._dates():
            print("Checking for date {date}".format(**locals()))
            for scraper in Scraper.objects.filter(active = True, run_daily = True):
                dedu = Deduplicate(articleset_1 = scraper.articleset.id, articleset_2 = scraper.articleset.id, headline_ratio=80, text_ratio=99)
                n_scraped = scraper.n_scraped_articles(from_date = date, to_date = date)
                n_scraped = date in n_scraped.keys() and n_scraped[date] or 0                
                print("{scraper}: {n_scraped}".format(**locals()))
                if  scraper.statistics and n_scraped < scraper.statistics[date.weekday()][0]:
                    print(scraper.statistics[date.weekday()][0])
                    print("added")
                    to_run.append((scraper.get_scraper(date = date),n_scraped))
                if not(scraper.statistics):
                    to_run.append((scraper.get_scraper(date = date),n_scraped))
            for s, n in to_run:
                s.run()

    def _dates(self):
        n_days = (self.options['last_date'] - self.options['first_date']).days
        for x in range(n_days + 1):
            yield self.options['first_date'] + timedelta(days = x)        


if __name__ == "__main__":
    from amcat.scripts.tools import cli
    cli.run_cli(FixGapsScript)
