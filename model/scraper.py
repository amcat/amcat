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
    class_name = models.CharField(max_length=50, db_index=True)
    verbose_name = models.CharField(max_length=100)

    username = models.CharField(max_length=50, null=True)
    password = models.CharField(max_length=25, null=True)
    email = models.EmailField(null=True)

    extra_data = JSONField()

    def get_data(self):
        return dict(username=self.username, password=self.password,
                    email=self.email, **self.extra_data)

    def __unicode__(self):
        return self.verbose_name
        
    class Meta():
        app_label = 'model'
        db_table = 'scrapers'

class Schedule(models.Model):
    scraper = models.ForeignKey(Scraper)

    interval = models.CharField(max_length=50)
    arguments = JSONField(help_text="JSON-object containing arguments",
                          db_column="arguments")

    class Meta():
        app_label = 'model'
        db_table = 'scrapers_schedules'

class Job(models.Model):
    started = models.DateTimeField(auto_now=True, db_index=True)
    ended = models.DateTimeField(null=True)

    arguments = JSONField()

    scraper = models.ForeignKey(Scraper, db_index=True)

    def __unicode__(self):
        return '%s started at %s' % (self.scraper.class_name, self.started)

    class Meta():
        app_label = 'model'
        db_table = 'scrapers_jobs'

    @property
    def output(self):
        """Get output from logs and return it"""
        return ''
