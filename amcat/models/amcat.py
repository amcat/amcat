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
import os
import logging;

from django.core.cache import cache
from django.db import models

from amcat.tools.model import AmcatModel


log = logging.getLogger(__name__)

WARNING_NOT_PRODUCTION = ("This is {server}. "
                           "Use <a href='http://amcat.vu.nl'>amcat.vu.nl</a> "
                           "unless you explicitly want to use this server. "
                          "Changes made here will probably <b>not</b> be saved")

SINGLETON_ID = 1

# Increment to current db version to trigger db upgrades that syncdb can't handle
# See amcat.tools.db_upgrader
CURRENT_DB_VERSION = 22

MEDIUM_CACHE_ENABLED = "medium_cache_enabled"
TIMEOUT_INFINITY = 31536000 # One year, actually. By then we should have upgraded to Django
                            # 1.6, which allows 'real' infinite caching.

class AmCAT(AmcatModel):
    id = models.BooleanField(primary_key=True, db_column="singleton_pk")

    global_announcement = models.TextField(blank=True, null=True)
    db_version = models.IntegerField()

    def save(self, *args, **kwargs):
        if self.id != SINGLETON_ID:
            raise NotImplementedError()
        super(AmCAT, self).save(*args, **kwargs)

    @classmethod
    def mediums_cache_enabled(self):
        return cache.get(MEDIUM_CACHE_ENABLED) or False

    @classmethod
    def enable_mediums_cache(self, enable=True):
        """
        Disable or enable articleset medium caching. This option can also be accessed
        via manage.py medium_cache [on|off].

        When off, various parts of AmCAT won't use project <--> mediums information
        although caches will always be updated when adding new sets / articles. This
        allows existing installations to build their caches while running.

        @param enable: Disables caching for mediums when set to False
        @return: None
        """
        return cache.set(MEDIUM_CACHE_ENABLED, enable, TIMEOUT_INFINITY)

    @property
    def server_warning(self):
        status = os.environ.get('AMCAT_SERVER_STATUS', '')
        if status != "production":
            if status:
                server = "the {status} server".format(**locals())
            else:
                server = "not the production server"
            return WARNING_NOT_PRODUCTION.format(**locals())

    @classmethod
    def get_instance(cls):
        try:
            return cls.objects.get(pk=SINGLETON_ID)
        except AmCAT.DoesNotExist:
            # create singleton here - don't use initial data as that will override db_version on syncdb
            return AmCAT.objects.create(db_version = CURRENT_DB_VERSION, id=SINGLETON_ID)


    class Meta():
        db_table = 'amcat_system'
        app_label = 'amcat'


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAmCAT(amcattest.AmCATTestCase):
    def test_get_instance(self):
        a = AmCAT.get_instance()
        self.assertEqual(type(a), AmCAT)

        os.environ['AMCAT_SERVER_STATUS']=""
        self.assertEqual(a.server_warning,
                         WARNING_NOT_PRODUCTION.format(server = "not the production server"))

        os.environ['AMCAT_SERVER_STATUS']="production"
        self.assertEqual(a.server_warning, None)
