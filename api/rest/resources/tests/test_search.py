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

import datetime
from api.rest.apitestcase import ApiTestCase
from amcat.tools import amcattest, toolkit
from amcat.tools import amcates


class TestSearch(ApiTestCase):
    @amcattest.use_elastic
    def test_dates(self):
        """Test whether date deserialization works, see #66"""
        for d in ('2001-01-01', '1992-12-31T23:59', '2012-02-29T12:34:56.789', datetime.datetime.now()):
            a = amcattest.create_test_article(date=d)
            amcates.ES().flush()
            res = self.get("/api/v4/search", ids=a.id)
            self.assertEqual(toolkit.read_date(res['results'][0]['date']), toolkit.read_date(str(d)))
