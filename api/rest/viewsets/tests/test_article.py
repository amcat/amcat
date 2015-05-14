import json
import datetime
from operator import itemgetter
from pprint import pprint
from django.test import Client
from rest_framework.test import APITestCase
from amcat.tools import amcattest
from amcat.tools import amcates
from amcat.tools import toolkit

URL = '/api/v4/projects/{project_id}/articlesets/{articleset_id}/articles/?format=json'

def create_test_article(n):
    return {
        "headline": str(n),
        "text": "test %s" % n,
        "date": datetime.date.today().isoformat(),
        "medium": amcattest.create_test_medium().name
    }

class TestArticleViewSet(APITestCase):
    def set_up(self):
        self.articleset = amcattest.create_test_set()
        self.user = self.articleset.project.owner
        self.client = Client()
        self.client.login(username=self.user.username, password="test")
        amcates.ES().flush()


    def get(self, url):
        return json.loads(Client().get(url + "?format=json").content)

    def post(self, url, data, as_user):
        c = Client()
        c.login(username=as_user.username, password="test")
        res = c.post(url + "?format=json", data)
        return res.status_code, json.loads(res.content)

    @amcattest.use_elastic
    def test_post(self):
        """Test whether posting and retrieving an article works correctly"""
        self.set_up()

        p = amcattest.create_test_project(owner=self.user)
        s = amcattest.create_test_set(project=p)
        a = {
            'date': datetime.datetime.now().isoformat(),
            'headline': 'Test child',
            'medium': 'Fantasy',
            'text': 'Hello Universe',
            'pagenr': 1,
            'url': 'http://example.org',
            'uuid': 'c691fadf-3c45-4ed6-93fe-f035b5f500af',
        }

        url = "/api/v4/projects/{p.id}/articlesets/{s.id}/articles/".format(**locals())
        self.post(url, a, self.user)
        amcates.ES().flush()

        res = self.get(url)["results"]
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["headline"], a['headline'])
        self.assertEqual(toolkit.readDate(res[0]["date"]), toolkit.readDate(a['date']))
        self.assertEqual(res[0]["uuid"], a['uuid'])
