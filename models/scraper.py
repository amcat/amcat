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
from amcat.forms.fields import JSONField

import json

class Scraper(models.Model):
    id = models.AutoField(primary_key=True, db_column="scraper_id")

    module = models.CharField(max_length=100)
    class_name = models.CharField(max_length=100)
    label = models.CharField(max_length=100)

    username = models.CharField(max_length=50, null=True)
    password = models.CharField(max_length=25, null=True)
    email = models.EmailField(null=True)

    run_daily = models.BooleanField(default=False)

    class Meta():
        app_label = 'amcat'
        db_table = 'scrapers'

    def get_scraper(self):
        module = __import__(self.module, fromlist=self.class_name)
        return getattr(module, self.class_name)




###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest



class TestScraperModel(amcattest.PolicyTestCase):
    def test_get_scraper(self):
        """Can we get a scraper from the db?"""

        s =Scraper.objects.create(module='amcat.models.scraper',
                                  class_name='TestScraperModel')
        self.assertEqual(s.get_scraper().__class__, TestScraperModel)
        


