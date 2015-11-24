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

from django.test.client import RequestFactory
from amcat.models import RecentProject

class TestRecentProjects(amcattest.AmCATTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_update_visited(self):
        u = amcattest.create_test_user()
        p = amcattest.create_test_project(owner=u)
        dt = datetime.now()
        (rp, _) = RecentProject.update_visited(u.userprofile, p, date_visited=dt)

        qs = RecentProject.objects.filter(user=u.userprofile, project=p, date_visited=dt)
        self.assertQuerysetEqual(qs, [repr(rp)])

    def test_ordered_by_time_desc(self):
        u = amcattest.create_test_user()
        profile = u.userprofile

        p1 = amcattest.create_test_project(owner=u)
        p2 = amcattest.create_test_project(owner=u)
        p3 = amcattest.create_test_project(owner=u)

        dt1 = datetime(2015, 8, 1)
        dt2 = datetime(2015, 7, 1)
        dt3 = datetime(2015, 9, 1)

        (rp1, _) = RecentProject.update_visited(profile, p1, date_visited=dt1)
        (rp2, _) = RecentProject.update_visited(profile, p2, date_visited=dt2)
        (rp3, _) = RecentProject.update_visited(profile, p3, date_visited=dt3)

        #latest date first
        order = [rp3, rp1, rp2]
        qs = RecentProject.get_recent_projects(profile)
        self.assertQuerysetEqual(qs, map(repr, order))

class TestUser(amcattest.AmCATTestCase):
    def test_create(self):
        """Test whether we can create a user"""
        u = amcattest.create_test_user()
        self.assertIsNotNone(u)