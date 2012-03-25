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

"""ORM Module representing scrapers"""

from django.db import models
from amcat.tools.model import AmcatModel

class Scraper(AmcatModel):
    __label__ = 'label'

    id = models.AutoField(primary_key=True, db_column="scraper_id")

    module = models.CharField(max_length=100)
    class_name = models.CharField(max_length=100)
    label = models.CharField(max_length=100)

    username = models.CharField(max_length=50, null=True)
    password = models.CharField(max_length=25, null=True)

    run_daily = models.BooleanField(default=False)

    # Storage options
    articleset = models.ForeignKey("amcat.ArticleSet", null=True)


    class Meta():
        app_label = 'amcat'
        db_table = 'scrapers'

    def get_scraper_class(self):
        module = __import__(self.module, fromlist=self.class_name)
        return getattr(module, self.class_name)

    def get_scraper(self, **options):
        scraper_class = self.get_scraper_class()
        scraper_options = dict(username=self.username, password=self.password)
        scraper_options.update(options)
        return scraper_class(**scraper_options)


def get_scrapers(**options):
    """Return all daily scrapers, instantiated with the given
    options plus information from the database"""
    for s in Scraper.objects.filter(run_daily=True):
        yield s.get_scraper(**options)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest


class TestScrapers(amcattest.PolicyTestCase):

    def test_get_scraper(self):
        """Can we get a scraper from the db?"""

        s =Scraper.objects.create(module='amcat.models.scraper',
                                  class_name='TestScraperModel')
        self.assertEqual(s.get_scraper_class(), TestScraperModel)



