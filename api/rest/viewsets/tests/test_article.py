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
    @amcattest.skip_TODO
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

    @amcattest.use_elastic
    def test_post_existing_uuid(self):
        self.set_up()

        p = amcattest.create_test_project(owner=self.user)
        s = amcattest.create_test_set(project=p)
        a = amcattest.create_test_article(articleset=s, text="But seriously..")

        url = "/api/v4/projects/{p.id}/articlesets/{s.id}/articles/".format(**locals())
        res = self.get(url)["results"]
        self.assertEqual(len(res), 1)


        article = res[0]
        article["text"] = "ABC."

        del article["pagenr"]
        del article["externalid"]
        del article["parent"]

        self.post(url, article, as_user=self.user)
        res = self.get(url)["results"]
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["text"], "But seriously..")


    @amcattest.use_elastic
    @amcattest.skip_TODO
    def test_children(self):
        self.set_up()

        p = amcattest.create_test_project()
        s = amcattest.create_test_set(project=p)
        # need to json dump the children because the django client does weird stuff with post data
        children = json.dumps([{'date': '2001-01-02', 'headline': 'Test child',
                                'medium': 'Fantasy', 'text': 'Hello Universe'}])
        a = {
            'date': '2001-01-01',
            'headline': 'Test parent',
            'medium': 'My Imagination',
            'text': 'Hello World',
            'children': children
        }
        url = "/api/v4/projects/{p.id}/articlesets/{s.id}/articles/".format(**locals())
        self.post(url, a, as_user=self.user)
        amcates.ES().flush()

        res = self.get(url)["results"]

        headlines = {a['headline'] : a for a in res}
        self.assertEqual(set(headlines), {'Test parent', 'Test child'})
        self.assertEqual(headlines['Test child']['parent'], headlines['Test parent']['id'])


    @amcattest.use_elastic
    @amcattest.skip_TODO
    def test_parent_attribute(self):
        """Can we add an article as a child to a specific existing article?"""
        self.set_up()

        s = amcattest.create_test_set()
        a = amcattest.create_test_article(articleset=s, project=s.project, headline="parent")
        b = {
            'date': '2001-01-01',
            'headline': 'child',
            'medium': 'My Imagination',
            'text': 'Hello World',
            'parent' : a.id
        }

        url = "/api/v4/projects/{a.project_id}/articlesets/{s.id}/articles/".format(**locals())
        self.post(url, b, as_user=self.user)

        articles = {a.headline : a for a in s.articles.all()}
        self.assertEqual(articles['child'].parent, articles['parent'])
