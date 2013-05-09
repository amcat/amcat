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

from django.db import models
from amcat.tools.model import AmcatModel
import os
import logging;
log = logging.getLogger(__name__)

ANNOUNCE_NOT_PRODUCTION = ("This is not the production server. "
                           "Use <a href='http://amcat.vu.nl'>amcat.vu.nl</a> "
                           "unless you explicitly want to use this server.")

class AmCAT(AmcatModel):
    id = models.BooleanField(primary_key=True, db_column="singleton_pk")

    def save(self, *args, **kwargs):
        raise NotImplementedError()
    
    global_announcement = models.TextField(blank=True, null=True)

    def get_announcement(self):
        status = os.environ.get('AMCAT_SERVER_STATUS', '')
        announcement = []
        if status != "production":
            announcement.append(ANNOUNCE_NOT_PRODUCTION)
            if status:
                announcement[-1] += " This server's status: "+status
        if self.global_announcement:
            announcement.append(self.global_announcement)
        return "<br/>\n".join(announcement)
        return announcement

    @classmethod
    def get_instance(cls):
        return cls.objects.get(pk=1)


    class Meta():
        db_table = 'amcat_system'
        app_label = 'amcat'


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAmCAT(amcattest.PolicyTestCase):
    def test_get_instance(self):
        a = AmCAT.get_instance()
        self.assertEqual(type(a), AmCAT)

        os.environ['AMCAT_SERVER_STATUS']=""
        self.assertEqual(a.get_announcement(), ANNOUNCE_NOT_PRODUCTION)

        os.environ['AMCAT_SERVER_STATUS']="production"
        self.assertEqual(a.get_announcement(), "")

        os.environ['AMCAT_SERVER_STATUS']="test"
        self.assertEqual(a.get_announcement(), ANNOUNCE_NOT_PRODUCTION + " This server's status: test")

        a.global_announcement = "Testing 123"
        os.environ['AMCAT_SERVER_STATUS']="production"
        self.assertEqual(a.get_announcement(), "Testing 123")
        
        os.environ['AMCAT_SERVER_STATUS']=""
        self.assertEqual(a.get_announcement(), ANNOUNCE_NOT_PRODUCTION + "<br/>\nTesting 123")
