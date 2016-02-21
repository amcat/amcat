import json
from django.test import Client, TestCase
from amcat.tools.amcattest import create_test_user


class TestMethodOverride(TestCase):
    """
    For large GET requests we would like to 'tunnel' over POST, to
    prevent (our) proxies from gobbling up the request.
    """
    def setUp(self):
        self.u1 = create_test_user()
        self.u2 = create_test_user()
        self.c = Client()
        self.c.login(username=self.u1.username, password="test")

    def test_get(self):
        url = "/api/v4/user?format=json&pk={self.u1.id}"
        users = self.c.get(url.format(**locals()))

        users = json.loads(users.content.decode("utf-8"))["results"]
        self.assertEqual(1, len(users))
        self.assertEqual(self.u1.id, users[0]["id"])

    def test_get_override(self):
        # Would have been X-HTTP-Method-Override, but Client doesn't convert
        # X-HTTP-Method-Override to a field 'HTTP_X_HTTP_METHOD_OVERRIDE' on
        # META. (Although Django in production does.)
        headers = {"HTTP_X_HTTP_METHOD_OVERRIDE": "GET"}
        params = {"pk": self.u1.id, "format": "json"}
        users = self.c.post("/api/v4/user", params, **headers)

        users = json.loads(users.content.decode("utf-8"))["results"]
        self.assertEqual(1, len(users))
        self.assertEqual(self.u1.id, users[0]["id"])

