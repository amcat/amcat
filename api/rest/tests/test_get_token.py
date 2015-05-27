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
from amcat.tools import amcattest
from api.rest.apitestcase import ApiTestCase
from api.rest.get_token import ObtainAuthToken


class TestObtainAuthToken(ApiTestCase):
    def setUp(self):
        self.user = amcattest.create_test_user()

    def test_non_active(self):
        self.user.is_active = False
        self.user.save()

        response = self.post("/api/v4/get_token", check_status=400, body={
            "username": self.user.username,
            "password": "test"
        })

        self.assertEqual(response["non_field_errors"][0], "User account is disabled.")

    def test_missing_fields(self):
        response = self.post("/api/v4/get_token", check_status=400, body={
            "password": "test"
        })

        self.assertIn("username", response)

    def test_wrong_credentials(self):
        response = self.post("/api/v4/get_token", check_status=400, body={
            "username": self.user.username,
            "password": "wrong-password"
        })

        self.assertEqual(response["non_field_errors"][0], "Unable to login with provided credentials.")


    def test_success(self):
        response = self.post("/api/v4/get_token", check_status=200, body={
            "username": self.user.username,
            "password": "test"
        })

        self.assertIn("token", response)
