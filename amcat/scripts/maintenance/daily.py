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

import datetime
from django import forms
import logging;log = logging.getLogger(__name__)

from amcat.scraping.controller import RobustController
from amcat.scripts.script import Script
from amcat.models.project import Project    
from amcat.models.articleset import ArticleSet
from amcat.models.scraper import Scraper

class DailyForm(forms.Form):
    date = forms.DateField()
    deduplicate = forms.BooleanField(required = False)

class DailyScript(Script):
    options_form = DailyForm

    def run(self, _input):
        scrapers = list(self.get_scrapers(date = self.options['date']))
        log.info("Starting scraping with {n} scrapers: {classnames}".format(
                n = len(scrapers),
                classnames = [s.__class__.__name__ for s in scrapers]))
        self.scrape(
            RobustController(), 
            scrapers, 
            self.options['deduplicate'] and True)

    def scrape(self, controller, scrapers, deduplicate = False):
        """Use the controller to scrape the given scrapers."""
        general_index_articleset = ArticleSet.objects.get(pk = 2)
        #CAUTION: destination articleset is hardcoded
        result = []
        current = None
        for a in controller.scrape(scrapers, deduplicate = deduplicate):
            result.append(a)
            if a.scraper != current:
                #new scraper started
                if a.scraper.module().split(".")[-2].lower().strip() == "newspapers":
                    #if scraper in newspapers module, add it's result to set 2
                    log.info("Adding {x} articles of {a.scraper.__class__.__name__} to general index set ({general_index_articleset})".format(x = len(result), **locals()))
                    general_index_articleset.add_articles(result)

                result = []
                current = a.scraper

    def get_scrapers(self, date=None, days_back=7, **options):
        """
        Return all daily scrapers as needed for the days_back days prior
        to the given date for which no articles are recorded. The scrapers
        are instantiated with the date, the given options, and information
        from the database
        """
        if date is None: date = datetime.date.today()
        dates = [date - datetime.timedelta(days=n) for n in range(days_back)]
        for s in Scraper.objects.filter(run_daily=True, active=True):
            for day in dates:
                if not self.satisfied(s, day):
                    try:
                        s_instance = s.get_scraper(date = day, **options)
                    except Exception:
                        log.exception("get_scraper for scraper {s.scraper_id} ({s.label}) failed".format(**locals()))
                    else:
                        yield s_instance

    def satisfied(self, scraper, day):
        """Has the scraper successfully run for the given date?"""
        n_scraped = scraper.n_scraped_articles(from_date = day, to_date = day)
        if not n_scraped:
            return False #no articles
        elif scraper.statistics == None:
            return False #don't know if enough articles, playing it safe
        elif n_scraped[day] <= scraper.statistics[day.weekday()][0]:
            return False #not enough articles
        else:
            return True


from amcat.tools.amcatlogging import AmcatFormatter
import sys

def setup_logging():
    loggers = (logging.getLogger("amcat.scraping"), logging.getLogger(__name__), logging.getLogger("scrapers"))
    d = datetime.date.today()
    filename = "/home/amcat/log/daily_{d.year:04d}-{d.month:02d}-{d.day:02d}.txt".format(**locals())
    sys.stderr = open(filename, 'a')
    handlers = (logging.FileHandler(filename), logging.StreamHandler())
    formatter = AmcatFormatter(date = True)

    for handler in handlers:
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)

    for logger in loggers:
        logger.setLevel(logging.INFO)
        for handler in handlers:        
            logger.addHandler(handler)

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    setup_logging()
    cli.run_cli(DailyScript)
