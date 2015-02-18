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

from datetime import datetime
from amcat.tools import amcattest
from amcat.tools.amcates import ES


class TestAggregate(amcattest.AmCATTestCase):
    def set_up(self):
        # We cannot use setUp, as use_elastic deletes indices
        aset = amcattest.create_test_set()

        m1 = amcattest.create_test_medium()
        m2 = amcattest.create_test_medium()
        a1 = amcattest.create_test_article(text="Foo", medium=m1, articleset=aset, date=datetime(2014, 4, 3))
        a2 = amcattest.create_test_article(text="Bar", medium=m1, articleset=aset, date=datetime(2015, 4, 3))
        a3 = amcattest.create_test_article(text="FooBar", medium=m2, articleset=aset)
        a4 = amcattest.create_test_article(text="BarFoo", medium=m2, articleset=aset, date=datetime(2014, 1, 3))

        ES().flush()
        return aset, m1, m2, a1, a2, a3, a4

   def test_empty(self):
       pass
