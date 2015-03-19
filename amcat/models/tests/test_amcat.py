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
import os

from amcat.models import WARNING_NOT_PRODUCTION
from amcat.models import AmCAT
from amcat.tools import amcattest


class TestAmCAT(amcattest.AmCATTestCase):
    def test_get_instance(self):
        a = AmCAT.get_instance()
        self.assertEqual(type(a), AmCAT)

        os.environ['AMCAT_SERVER_STATUS'] = ""
        self.assertEqual(a.server_warning,
                         WARNING_NOT_PRODUCTION.format(server="not the production server"))

        os.environ['AMCAT_SERVER_STATUS'] = "production"
        self.assertEqual(a.server_warning, None)