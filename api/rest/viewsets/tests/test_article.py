from rest_framework.reverse import reverse
from uuid import uuid4
import json
import datetime
from operator import itemgetter
from pprint import pprint
from django.test import Client
from rest_framework.test import APITestCase
from amcat.tools import amcattest
from amcat.tools import amcates
from amcat.tools import toolkit
from amcat.models import Article

def test_article(**kwargs):
    if 'date' not in kwargs: kwargs['date'] = datetime.datetime.now().isoformat()
    if 'headline' not in kwargs: kwargs['headline'] = 'test headline {}'.format(uuid4())
    if 'text' not in kwargs: kwargs['text'] = 'test text {}'.format(uuid4())
    if 'medium' not in kwargs: kwargs['medium'] = 'test'
    return kwargs    


class TestArticleViewSet(APITestCase):
    def setUp(self):
        self.project = amcattest.create_test_project()
        self.user = self.project.owner
        self.setUp_set()

    def setUp_set(self):
        self.aset = amcattest.create_test_set(project=self.project)
        #self.url = reverse("api:article") + "?format=json"
        self.url_set = reverse("api:project-articleset-article-list",
                               kwargs=dict(project=self.project.id, articleset=self.aset.id)) + "?format=json"

    def url_article(self, aid):
        return reverse("api:project-articleset-article-details",
                       kwargs=dict(project=self.project.id, articleset=self.aset.id, id=aid)) + "?format=json"


    def _get_articles(self, expected_status=200, as_user="self.user"):
        if as_user == "self.user": as_user = self.user
        if as_user:
            self.client.login(username=as_user.username, password="test")
        response = Client().get(self.url_set)
        self.assertEqual(response.status_code, expected_status,
                         "Status code {response.status_code}: {response.content}".format(**locals()))
        return json.loads(response.content)


    def _post_articles(self, data, to_set=True, expected_status=201, as_user="self.user"):
        if as_user == "self.user": as_user = self.user
        if as_user:
            self.client.login(username=as_user.username, password="test")
        url = self.url_set if to_set else self.url
        response = self.client.post(url, content_type="application/json", data=json.dumps(data))
        self.assertEqual(response.status_code, expected_status,
                         "Status code {response.status_code}: {response.content}".format(**locals()))
        amcates.ES().flush()
        return json.loads(response.content)
            

    @amcattest.use_elastic
    def test_post(self):
        """Test whether posting and retrieving an article works correctly"""
        a = test_article()
        res = self._post_articles(a)
        self.assertEqual(set(res.keys()), {'id'}) # POST should only return IDs
        res = self._get_articles()["results"]
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["headline"], a['headline'])
        self.assertEqual(toolkit.readDate(res[0]["date"]), toolkit.readDate(a['date']))
        self.assertIsNotNone(res[0]["uuid"])

        # can we post explicit UUID?
        self.setUp_set()
        a['uuid'] = unicode(uuid4())
        self._post_articles(a)
        res = self._get_articles()["results"]
        self.assertEqual(res[0]["uuid"], a['uuid'])

    @amcattest.use_elastic
    def test_dupe(self):
        """Test whether deduplication works"""
        m = amcattest.create_test_medium()
        a = test_article(medium=m.name)
        aid1 = self._post_articles(a)['id']
        self.setUp_set()
        aid2 = self._post_articles(a)['id']

        # are the resulting ids identical?
        self.assertEqual(aid1, aid2)
        # is it not added (ie we only have one article with this medium)
        self.assertEqual(set(amcates.ES().query_ids(filters={'mediumid':m.id})), {aid1})
        # is it added to elastic for this set?
        self.assertEqual(set(amcates.ES().query_ids(filters={'sets':self.aset.id})), {aid1})


    @amcattest.use_elastic
    def test_post_multiple(self):

        a1, a2 = [test_article() for _ in [1,2]]

        result = self._post_articles([a1,a2])
        self.assertEqual(2, len(result))
        self.assertEqual(set(result[0].keys()), {'id'}) # POST should only return IDs

        arts = [Article.objects.get(pk=a["id"]) for a in result]

        self.assertEqual(arts[0].headline, a1['headline'])
        self.assertEqual(arts[1].headline, a2['headline'])
        
        # Are the articles added to the index?
        amcates.ES().flush()
        self.assertEqual(len(set(amcates.ES().query_ids(filters={"sets": self.aset.id}))), 2)
        
    @amcattest.use_elastic
    def test_post_children(self):
        self.client.login(username=self.user.username, password="test", to_set=True)

        a1, a2, a3, a4 = [test_article() for _ in [1,2,3,4]]
        a1['children'] = [a2]
        a2['children'] = [a3]

        result = self._post_articles([a1,a4])
        self.assertEqual(4, len(result))

        arts = [Article.objects.get(pk=a["id"]) for a in result]

        self.assertEqual(arts[0].headline, a1['headline'])
        self.assertEqual(arts[3].headline, a4['headline'])

        self.assertEqual(arts[0].parent, None)
        self.assertEqual(arts[1].parent, arts[0])
        self.assertEqual(arts[2].parent, arts[1])
        self.assertEqual(arts[3].parent, None)
        
        # Are the articles added to the index?
        amcates.ES().flush()
        self.assertEqual(len(set(amcates.ES().query_ids(filters={"sets": self.aset.id}))), 4)


    @amcattest.use_elastic
    def test_post_parent(self):
        article = amcattest.create_test_article()
        amcates.ES().flush()
        
        result, = self._post([test_article(parent=article.id)])
        new_article = Article.objects.get(id=result["id"])
        self.assertEqual(article, new_article.parent)

        # test posting existing uuid
        result, = self._post([test_article(parent=article.uuid)])
        new_article = Article.objects.get(id=result["id"])
        self.assertEqual(article, new_article.parent)

        # test posting article and child with uuid
        p = test_article(uuid=unicode(uuid4()))
        c = test_article(parent=p['uuid'])
        result = self._post([p,c])
        pa, ca = [Article.objects.get(pk=a["id"]) for a in result]
        self.assertEqual(pa, ca.parent)
        
        
