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

from django.test import Client
from rest_framework.authtoken.models import Token

from amcat.models import ROLE_PROJECT_METAREADER, Role, ProjectRole
from amcat.tools import amcattest
from api.rest.apitestcase import ApiTestCase
from api.rest.get_token import ObtainAuthToken

# Doesn't make much sense to put it anywhere else?
class TestTokenAuth(ApiTestCase):
    def setUp(self):
        self.user = amcattest.create_test_user()
        self.project = amcattest.create_test_project(guest_role=None)

        ProjectRole.objects.create(
            user=self.user,
            project=self.project,
            role=Role.objects.get(id=ROLE_PROJECT_METAREADER)
        )

    def test_no_authenticated(self):
        url = "/api/v4/projects/{id}/articlesets/".format(id=self.project.id)
        self.get(url, check_status=401)

    def test_authenticated(self):
        url = "/api/v4/projects/{id}/articlesets/".format(id=self.project.id)

        self.assertEqual(0, Token.objects.all().count())
        token = self.post("/api/v4/get_token", {}, check_status=200, as_user=self.user)["token"]
        self.assertEqual(1, Token.objects.all().count())

        get_token = lambda: Token.objects.get(key=token)

        # Check 47 hours
        token = get_token()
        token.created = datetime.datetime.now() - datetime.timedelta(hours=47)
        token.save()

        response = Client().get(url, HTTP_AUTHORIZATION="Token {}".format(token))
        self.assertEqual(response.status_code, 200)

        # Test if request reset the token again
        self.assertLessEqual(get_token().created, datetime.datetime.now())
        self.assertLessEqual(datetime.datetime.now() - get_token().created, datetime.timedelta(minutes=5))

        # Check 49 hours
        token = get_token()
        token.created = datetime.datetime.now() - datetime.timedelta(hours=49)
        token.save()

        response = Client().get(url, HTTP_AUTHORIZATION="Token {}".format(token))
        self.assertEqual(response.status_code, 401)


class TestObtainAuthToken(ApiTestCase):
    def setUp(self):
        self.user = amcattest.create_test_user()

    def test_get_token_with_session_id(self):
        self.post("/api/v4/get_token", {}, check_status=400)
        self.post("/api/v4/get_token", {}, check_status=200, as_user=self.user)

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

        self.assertIn("username", response["non_field_errors"][0])

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
