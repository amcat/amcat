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

from amcat.scraping.scraper import DatedScraper, DBScraper, MultiScraper
from amcat.models.scraper import Scraper, get_scrapers
from datetime import date
from amcat.models.article import Article
from amcat.scraping.controller import SimpleController, ThreadedController, scrape_logged

import logging; log = logging.getLogger(__name__)

class TestDatedScraper(DatedScraper):
    medium_name = 'test_mediumxyz'
    def _get_units(self):
        return "abcd"
    def _scrape_unit(self, unit):
        yield Article(headline=unit, section="TestDatedScraper")

class TestDBScraper(DBScraper):
    medium_name = 'test_medium2'
    def _login(self, username, password):
        self.username = username
    def _get_units(self):
        return [1,2,3,4,5]
    def _scrape_unit(self, unit):
        log.debug("Scraping %i" % unit)
        if getattr(self, "username", None) is None:
            raise Exception("Not logged in!")
        yield Article(headline=unit, section="TestDBScraper")


class TestErrorScraper(DatedScraper):
    medium_name = 'test_mediumxyz'
    def __init__(self, *args, **kargs):
        super(TestErrorScraper, self).__init__(self, *args, **kargs)
        self.ue = 1
        self.se = 2
    def _get_units(self):
        if self.ue:
            self.ue -= 1
            raise Exception("Error from scraper._get_units")
        return "abcd"
    def _scrape_unit(self, unit):
        if self.se:
            self.se -= 1
            raise Exception("Error from scraper._scrape_unit")

        yield Article(headline=unit, section="TestDatedScraper")
    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest, amcatlogging

def _project_headlineset(project):
    return set(a.headline for a in project.articles.all())
    
class TestScraping(amcattest.PolicyTestCase):
    def setUp(self):
        Scraper.objects.all().delete()
        self.ds = Scraper.objects.create(module='amcat.tests.test_scraping',
                                         class_name='TestDatedScraper', run_daily=True)
        self.dbs =Scraper.objects.create(module='amcat.tests.test_scraping',
                                         class_name='TestDBScraper', run_daily=True,
                                         username='test', password='test')
        self.project = amcattest.create_test_project(name='scrapetest')
    
    def test_get_scrapers(self):
        scrapers = set(get_scrapers(date=date.today(), project=self.project.id))        
        self.assertEqual({s.__class__ for s in scrapers}, {TestDatedScraper, TestDBScraper})

        
    def test_run_scraper(self):
        self.project.articles.all().delete()
        s = self.ds.get_scraper(date = date.today(), project=self.project.id)
        articles = set(SimpleController().scrape(s))
        self.assertEqual(set(self.project.articles.all()), articles)
        self.assertEqual(set("abcd"), _project_headlineset(self.project))

    def test_multi_scraper(self):
        p2 = amcattest.create_test_project(name="test2")
        ds = self.ds.get_scraper(date = date.today(), project=self.project.id)
        dbs = self.dbs.get_scraper(date = date.today(), project=p2.id)
        m = MultiScraper([ds, dbs])
        articles = SimpleController().scrape(m)
        self.assertEqual(set("abcd"), _project_headlineset(self.project))
        self.assertEqual(set("12345"), _project_headlineset(p2))
        self.assertEqual(len("abcd"), len([a for a in articles if a.scraper == ds]))
        self.assertEqual(len("12345"), len([a for a in articles if a.scraper == dbs]))

    def test_logged_scraper(self):
        ds = self.ds.get_scraper(date = date.today(), project=self.project.id)
        dbs = self.dbs.get_scraper(date = date.today(), project=self.project.id)
        
        counts, log = scrape_logged(SimpleController(), [ds, dbs])
        counts = {c.__class__.__name__ : n for (c,n) in counts.items()}
        self.assertEqual(counts, dict(TestDatedScraper=4, TestDBScraper=5))

        self.assertIn("DEBUG] Scraping 5", log)

        
    def test_medium_name(self):
        from amcat.models.medium import Medium
        
        Medium.objects.all().delete()
        self.assertRaises(Medium.DoesNotExist,
                          Medium.objects.get, name=TestDatedScraper.medium_name)
        s = self.ds.get_scraper(date = date.today(), project=self.project.id)
        self.assertEqual(s.medium.name, TestDatedScraper.medium_name)
        self.assertEqual(Medium.objects.get(name=TestDatedScraper.medium_name), s.medium)
        
        
