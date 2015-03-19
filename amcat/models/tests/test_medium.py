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
from amcat.models import to_medium_ids, Medium

from amcat.tools import amcattest


class TestMedium(amcattest.AmCATTestCase):
    def test_to_medium_ids(self):
        arts = amcattest.create_test_set(2).articles.all()
        m1, m2 = amcattest.create_test_medium(), amcattest.create_test_medium()
        self.assertEqual(set(to_medium_ids(m1)), {m1.id, })
        self.assertEqual(set(to_medium_ids([m1, m2])), {m1.id, m2.id})
        self.assertEqual(set(to_medium_ids(Medium.objects.filter(id__in=[m1.id, m2.id]))), {m1.id, m2.id})
        self.assertEqual(set(to_medium_ids(arts.values_list("medium__id", flat=True))), {a.medium_id for a in arts})
