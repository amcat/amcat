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
from datetime import date

from amcat.models import Scraper
from amcat.tools import amcattest


class TestScrapers(amcattest.AmCATTestCase):
    def test_get_scraper(self):
        """Can we get a scraper from the db?"""

        s = Scraper.objects.create(module='amcat.models.tests.test_scraper',
                                   class_name='TestScrapers')
        self.assertEqual(s.get_scraper_class().__name__, 'TestScrapers')

    def test_recent_articles(self):
        aset = amcattest.create_test_set()
        scraper = Scraper.objects.create(
            module='amcat.models.scraper',
            class_name='TestScraperModel',
            articleset=aset
        )

        for _date in ['2010-01-01'] * 3 + ['2010-01-03'] * 5 + ['2009-01-01'] * 6:
            aset.add(amcattest.create_test_article(date=_date))

        self.assertEqual(scraper.n_scraped_articles(), {
            date(2010, 1, 3): 5, date(2010, 1, 1): 3, date(2009, 1, 1): 6
        })

        self.assertEqual(scraper.n_scraped_articles(from_date='2010-01-01'), {
            date(2010, 1, 3): 5, date(2010, 1, 1): 3
        })

        aset.add(amcattest.create_test_article(date='2010-01-01 13:45'))
        self.assertEqual(scraper.n_scraped_articles(from_date='2010-01-01'), {
            date(2010, 1, 3): 5, date(2010, 1, 1): 4
        })


