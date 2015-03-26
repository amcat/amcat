import json
import datetime
from operator import itemgetter
from django.test import Client
from amcat.tools import amcattest
from amcat.tools import amcates

URL = '/api/v4/projects/{project_id}/articlesets/{articleset_id}/articles/?format=json'

def create_test_article(n):
    return {
        "headline": str(n),
        "text": "test %s" % n,
        "date": datetime.date.today().isoformat(),
        "medium": amcattest.create_test_medium().name
    }

class TestArticleViewSet(amcattest.AmCATTestCase):
    def set_up(self):
        self.articleset = amcattest.create_test_set()
        self.user = self.articleset.project.owner
        self.client = Client()
        self.client.login(username=self.user.username, password="test")
        amcates.ES().flush()

    @amcattest.use_elastic
    def test_create_articles_order(self):
        self.set_up()

        articleset_id = self.articleset.id
        project_id = self.articleset.project.id
        url = URL.format(**locals())

        r = json.loads(self.client.get(url).content)
        self.assertEqual([], r["results"])

        # Create some articles
        article_1 = create_test_article(0)
        article_1["children"] = [create_test_article(1), create_test_article(2)]
        article_2 = create_test_article(3)
        article_2["children"] = [create_test_article(4), create_test_article(5)]

        articles = json.dumps([article_1, article_2])

        r = self.client.post(url, articles, content_type="application/json")
        self.assertEqual(201, r.status_code)

        ids = map(int, [a["headline"] for a in json.loads(r.content)])
        self.assertEqual([0, 1, 2, 3, 4, 5], ids)
        self.assertEqual(6, len(json.loads(r.content)))

