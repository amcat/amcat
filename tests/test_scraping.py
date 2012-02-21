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

"""Test module for creating scrapers using the DB

Implemented as separate module because it creates new script classes that
would otherwise be imported and because it combines functionality of the
model.scraper, scraping.scraper, and scraping.controller modules
"""

from amcat.scraping.scraper import DatedScraper, DBScraper
from amcat.models.scraper import Scraper, get_scrapers
from datetime import date
from amcat.models.article import Article

class TestDatedScraper(DatedScraper):
    def get_units(self):
        self.output = []
        return "abcd"
    def scrape_unit(self, unit):
        return Article(headline=unit, 
        self.output.unit.upper()

class TestDBScraper(DBScraper):
    def get_units(self):
        self.output


    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest, amcatlogging

class TestScraping(amcattest.PolicyTestCase):
    def setUp(self):
        Scraper.objects.all().delete()
        ds = Scraper.objects.create(module='amcat.tests.test_scraping',
                                  class_name='TestDatedScraper', run_daily=True)
        dbs =Scraper.objects.create(module='amcat.tests.test_scraping',
                                  class_name='TestDBScraper', run_daily=True,
                                    username='test', password='test')
    
    def test_get_scrapers(self):
        scrapers = set(get_scrapers(date=date.today()))        
        self.assertEqual({s.__class__ for s in scrapers}, {TestDatedScraper, TestDBScraper})

    def test_multiscraper(self):
        scrapers = set(get_scrapers(date=date.today()))     
        s = MultiScraper
