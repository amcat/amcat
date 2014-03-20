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
from __future__ import unicode_literals, print_function, absolute_import

"""ORM Module representing scrapers"""

import datetime
from django.db import models
from amcat.tools.model import AmcatModel
from amcat.tools.djangotoolkit import JsonField
import json
import logging; log = logging.getLogger(__name__)

class Scraper(AmcatModel):
    __label__ = 'label'

    id = models.AutoField(primary_key=True, db_column="scraper_id")

    module = models.CharField(max_length=100)
    class_name = models.CharField(max_length=100)
    label = models.CharField(max_length=100)

    username = models.CharField(max_length=50, null=True)
    password = models.CharField(max_length=25, null=True)

    run_daily = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    # Storage options
    articleset = models.ForeignKey("amcat.ArticleSet", null=True)

    statistics = JsonField(null=True)

    class Meta():
        app_label = 'amcat'
        db_table = 'scrapers'

    def get_scraper_class(self):
        module = __import__(self.module, fromlist=self.class_name)
        return getattr(module, self.class_name)

    def get_scraper(self, **options):
        scraper_class = self.get_scraper_class()

        scraper_options = {
            'username' : self.username,
            'password' : self.password,
            'project' : self.articleset.project.id,
            'articleset' : self.articleset.id
        }

        scraper_options.update(options)
        return scraper_class(**scraper_options)

    def n_scraped_articles(self, from_date=None, to_date=None, medium = None):
        """
        Get the number of scraped articles per day for the given period.
        """
        if self.articleset is None:
            raise Exception("Cannot count articles if scraper has no article set")
        # select and filter articles
        q = self.articleset.articles.all()
        if to_date: q = q.filter(date__lte=to_date)
        if from_date: q = q.filter(date__gte=from_date)
        first = q.order_by('date').first()
        if first and first.insertscript:
            # It's safe to use the 'insertscript' attribute, which was added later
            scraper_class = self.get_scraper_class()
            q = q.filter(insertscript = scraper_class.__name__)
        else:
            if medium: q = q.filter(medium = medium.id)

        # aggregate count group by date, return as dict
        q = q.extra(select=dict(d="cast(date as date)")).values_list("d")
        q = q.annotate(models.Count("id"))
        return dict(q)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest


class TestScrapers(amcattest.AmCATTestCase):

    def test_get_scraper(self):
        """Can we get a scraper from the db?"""

        s =Scraper.objects.create(module='amcat.models.scraper',
                                  class_name='TestScrapers')
        self.assertEqual(s.get_scraper_class().__name__, 'TestScrapers')

    def test_recent_articles(self):
        # DOES NOT WORK WITH SQLITE
        import settings
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            return
        s = amcattest.create_test_set()
        sc =Scraper.objects.create(module='amcat.models.scraper',
                                  class_name='TestScraperModel', articleset=s)
        for date in ['2010-01-01'] * 3 + ['2010-01-03'] * 5 + ['2009-01-01'] * 6:
            s.add(amcattest.create_test_article(date=date))

        from amcat.tools.toolkit import writeDate
        normalize = lambda nn : dict((writeDate(k), v) for (k,v,) in nn.items())
        self.assertEqual(normalize(sc.n_scraped_articles()),
                         {'2010-01-03': 5, '2010-01-01': 3, '2009-01-01': 6})
        self.assertEqual(normalize(sc.n_scraped_articles(from_date='2010-01-01')),
                         {'2010-01-03': 5, '2010-01-01': 3})
        s.add(amcattest.create_test_article(date='2010-01-01 13:45'))
        self.assertEqual(normalize(sc.n_scraped_articles(from_date='2010-01-01')),
                         {'2010-01-03': 5, '2010-01-01': 4})


