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
from django.test.client import Client

from amcat.models import Role, ProjectRole, User
from amcat.tools import amcattest


class TestUserViews(amcattest.AmCATTestCase):
    def post(self, url, as_user, data):
        c = Client()
        c.login(username=as_user.username, password="test")
        return c.post(url, data)

    def test_project_user_add(self):
        project = amcattest.create_test_project()
        project_admin = User.objects.first()

        plebs = amcattest.create_test_user()
        admin = amcattest.create_test_user()
        admin.is_superuser = True
        admin.save()

        url = "/projects/{}/users/add/".format(project.id)

        # Adding a user as plebs should not be possible
        self.assertEqual(1, ProjectRole.objects.count())
        admin_role = Role.objects.get(label="admin", projectlevel=True)
        response = self.post(url, plebs, {"role": admin_role.id, "user": plebs.id})
        self.assertEqual(403, response.status_code)
        self.assertEqual(1, ProjectRole.objects.count())

        # Adding as superuser should be possible
        reader_role = Role.objects.get(label="reader", projectlevel=True)
        response = self.post(url, admin, {"role": reader_role.id, "user": plebs.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(2, ProjectRole.objects.count())

        # Plebs gonna be plebs
        admin_role = Role.objects.get(label="admin", projectlevel=True)
        response = self.post(url, plebs, {"role": admin_role.id, "user": plebs.id})
        self.assertEqual(403, response.status_code)
        self.assertEqual(2, ProjectRole.objects.count())

        # Test remove if admin on project
        response = self.post(url, project_admin, {"role": "", "user": plebs.id})
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, ProjectRole.objects.count())


