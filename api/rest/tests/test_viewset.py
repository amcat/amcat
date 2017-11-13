import json
from uuid import uuid4

from django.test import Client
from amcat.tools import amcattest
from api.rest.viewset import AmCATViewSetMixin


class TestSearchViewSetMixin(amcattest.AmCATTestCase):
    def setUp(self):
        self.client = Client()
        project = amcattest.create_test_project()
        amcattest.create_test_set(name="foo", project=project)
        amcattest.create_test_set(name="bar", project=project)

        self.url = "/api/v4/projects/{project.id}/articlesets/?format=json"
        self.url = self.url.format(**locals())

    def _get_json(self, url):
        self.user = amcattest.create_test_user(username="user_{!s:.7s}".format(uuid4()), password="password")
        c = Client()
        c.login(username=self.user.username, password="password")
        r = c.get(url)
        self.assertEqual(r.status_code, 200)
        return json.loads(r.content.decode('utf-8'))

    def test_basic(self):
        # No search parameter
        results = self._get_json(self.url)
        self.assertEqual(2, results['total'])

        # Foo parameter
        results = self._get_json(self.url + "&search=foo")
        self.assertEqual(1, results['total'])
        self.assertEqual("foo", results["results"][0]["name"])

        # Bar paramter
        results = self._get_json(self.url + "&search=bar")
        self.assertEqual(1, results['total'])
        self.assertEqual("bar", results["results"][0]["name"])

    def test_case_insensitivity(self):
        results = self._get_json(self.url + "&search=BaR")
        self.assertEqual(1, results['total'])
        self.assertEqual("bar", results["results"][0]["name"])

    def test_partial(self):
        results = self._get_json(self.url + "&search=fo")
        self.assertEqual(1, results['total'])
        self.assertEqual("foo", results["results"][0]["name"])

        results = self._get_json(self.url + "&search=oo")
        self.assertEqual(1, results['total'])
        self.assertEqual("foo", results["results"][0]["name"])

        results = self._get_json(self.url + "&search=a")
        self.assertEqual(1, results['total'])
        self.assertEqual("bar", results["results"][0]["name"])


class AmCATViewSetMixinTest(amcattest.AmCATTestCase):
    def test_get_url_pattern(self):
        class AMixin(AmCATViewSetMixin):
            model_key = "project"

        class BMixin(AmCATViewSetMixin):
            model_key = "codebook"

        class CMixin(BMixin):
            pass

        class AViewSet(AMixin, BMixin): pass
        class BViewSet(AMixin, CMixin): pass
        class CViewSet(BMixin, AMixin): pass

        self.assertEquals(r"projects", AMixin.get_url_pattern())
        self.assertEquals(r"codebooks", BMixin.get_url_pattern())
        self.assertEquals(r"projects/(?P<project>\d+)/codebooks", AViewSet.get_url_pattern())
        self.assertEquals(r"projects/(?P<project>\d+)/codebooks", BViewSet.get_url_pattern())
        self.assertEquals(r"codebooks/(?P<codebook>\d+)/projects", CViewSet.get_url_pattern())
