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
from amcat.models import Scraper
from amcat.tools import amcattest


class TestScrapers(amcattest.AmCATTestCase):
    def test_get_scraper(self):
        """Can we get a scraper from the db?"""

        s = Scraper.objects.create(module='amcat.models.tests.test_scraper',
                                   class_name='TestScrapers')
        self.assertEqual(s.get_scraper_class().__name__, 'TestScrapers')

    def test_recent_articles(self):
        # DOES NOT WORK WITH SQLITE
        import settings

        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            return
        s = amcattest.create_test_set()
        sc = Scraper.objects.create(module='amcat.models.scraper',
                                    class_name='TestScraperModel', articleset=s)
        for date in ['2010-01-01'] * 3 + ['2010-01-03'] * 5 + ['2009-01-01'] * 6:
            s.add(amcattest.create_test_article(date=date))

        from amcat.tools.toolkit import writeDate

        normalize = lambda nn: dict((writeDate(k), v) for (k, v,) in nn.items())
        self.assertEqual(normalize(sc.n_scraped_articles()),
                         {'2010-01-03': 5, '2010-01-01': 3, '2009-01-01': 6})
        self.assertEqual(normalize(sc.n_scraped_articles(from_date='2010-01-01')),
                         {'2010-01-03': 5, '2010-01-01': 3})
        s.add(amcattest.create_test_article(date='2010-01-01 13:45'))
        self.assertEqual(normalize(sc.n_scraped_articles(from_date='2010-01-01')),
                         {'2010-01-03': 5, '2010-01-01': 4})


