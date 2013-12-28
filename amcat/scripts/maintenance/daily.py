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

from amcat.scraping.controller import Controller, ThreadedAPIController, ThreadedController
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
        log.info("Getting scrapers...")
        scrapers = list(self.get_scrapers(date = self.options['date']))
        print([s.__class__.__name__ for s in scrapers])
        log.info("Starting scraping with {n} scrapers: {classnames}".format(
                n = len(scrapers),
                classnames = [s.__class__.__name__ for s in scrapers]))
        self.scrape(Controller(), scrapers)

    def scrape(self, controller, scrapers, deduplicate = False):
        """Use the controller to scrape the given scrapers."""
        if isinstance(controller, ThreadedController):
            controller.run(scrapers)
        else:
            [a for a in controller.run(scrapers)] #unpack generator

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
                        import traceback
                        exc = traceback.format_exc()
                        print(exc)
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
    loggers = (logging.getLogger("amcat"), logging.getLogger("scrapers"),
               logging.getLogger("__main__"), logging.getLogger("celery"))
    d = datetime.date.today()
    filename = "/home/amcat/log/daily_{d.year:04d}-{d.month:02d}-{d.day:02d}.txt".format(**locals())
    sys.stderr = open(filename, 'a')
    #TODO: Point sys.stderr to both console and file
    handlers = (logging.StreamHandler(sys.stdout),logging.FileHandler(filename))
    formatter = AmcatFormatter(date = True)

    for handler in handlers:
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)

    for logger in loggers:
        logger.propagate = False
        logger.setLevel(logging.INFO)
        for handler in handlers:        
            logger.addHandler(handler)
    logging.getLogger().handlers = []

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    setup_logging()
    cli.run_cli(DailyScript)
