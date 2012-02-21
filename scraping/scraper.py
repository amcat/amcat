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
A Scraper is an object that knows how to scrape a certain resource. A scraper
is called by the controller, 
"""

from django import forms

from amcat.scripts.script import Script
from amcat.models.article import Article

from amcat.scripts.tools import cli
from amcat.scraping.htmltools import HTTPOpener

import logging; log = logging.getLogger(__name__)

class Scraper(Script):
    output_type = Article

    def run(self, input):
        log.info("Getting units...")
        for u in self.get_units():
            log.info("Scraping unit %s" % getattr(u.props, "url", None))
            for a in self.scrape_unit(u):
                log.info("Article: %s" % a)
    
    def get_units(self):
        return [None]

    def scrape_unit(self, unit):
        return []

class DateForm(forms.Form):
    """
    Form for scrapers that operate on a date
    """
    date = forms.DateField()

class DatedScraper(Scraper):
    """Base class for scrapers that work for a certain date"""
    options_form = DateForm
    
class DBScraperForm(DateForm):
    """
    Form for dated scrapers that need credentials
    """
    username = forms.CharField()
    password = forms.CharField()

class DBScraper(Scraper):
    """Base class for (dated) scrapers that require a login"""
    options_form = DBScraperForm

class HTTPScraper(Scraper):
    """Base class for scrapers that require an http opener"""
    def __init__(self, *args, **kargs):
        super(HTTPScraper, self).__init__(*args, **kargs)
        self.opener = HTTPOpener()
    def getdoc(self, url):
        """Legacy/convenience function"""
        return self.opener.getdoc(url)



class MultiScraper(object):
    """
    Class that encapsulated multiple scrapers behind a single scraper interface
    Does not formally inherit from Scraper because it is not a runnable script
    """

    def __init__(self, scrapers):
        """@param scrapers: instantiated Scraper objects ('Ready to start scraping') """
        self.scrapers = scrapers

    def get_units(self):
        for scraper in self.scrapers:
            for unit in scraper.get_units():
                yield (scraper, unit)

    def scrape_unit(self, unit):
        (scraper, unit) = unit
        scraper.scrape_unit(unit)

