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
    if 'title' not in kwargs: kwargs['title'] = 'test headline {}'.format(uuid4())
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

    def url_set(self, setid=None, projectid=None, text=False):
        if setid is None: setid = self.aset.id
        if projectid is None: projectid = self.project.id
        url = reverse("api:project-articleset-article-list",
                      kwargs=dict(project=projectid, articleset=setid)) + "?format=json"
        if text:
            url += "&text=True"
        return url
        
    def url_article(self, aid, projectid=None, setid=None, text=False):
        if setid is None: setid = self.aset.id
        if projectid is None: projectid = self.project.id
        url = reverse("api:project-articleset-article-detail",
                      kwargs=dict(project=projectid, articleset=setid, pk=aid)) + "?format=json"
        if text:
            url += "&text=True"
        return url


    def _get_articles(self, expected_status=200, as_user="self.user", **url_kwargs):
        if as_user == "self.user": as_user = self.user
        if as_user:
            self.client.login(username=as_user.username, password="test")
        else:
            self.client.logout()
        url = self.url_set(**url_kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, expected_status,
                         "Status code {response.status_code}: {response.content}".format(**locals()))
        return json.loads(response.content.decode(response.charset))

    def _get_article(self, aid, expected_status=200, as_user="self.user", **url_kwargs):
        if as_user == "self.user": as_user = self.user
        if as_user:
            self.client.login(username=as_user.username, password="test")
        else:
            self.client.logout()
        response = Client().get(self.url_article(aid, **url_kwargs))
        self.assertEqual(response.status_code, expected_status,
                         "Status code {response.status_code}: {response.content}".format(**locals()))
        return json.loads(response.content.decode(response.charset))


    def _post_articles(self, data, expected_status=201, as_user="self.user", return_json=None, **url_kwargs):
        if as_user == "self.user": as_user = self.user
        if return_json is None:
            return_json = (expected_status // 100) == 2
        if as_user:
            self.client.login(username=as_user.username, password="test")
        else:
            self.client.logout()
        url = self.url_set(**url_kwargs)
        response = self.client.post(url, content_type="application/json", data=json.dumps(data))
        self.assertEqual(response.status_code, expected_status,
                         "Status code {response.status_code}: {response.content}".format(**locals()))
        
        amcates.ES().flush()
        if return_json:
            return json.loads(response.content.decode(response.charset))
        else:
            return response
            

    @amcattest.use_elastic
    def test_post(self):
        """Test whether posting and retrieving an article works correctly"""
        a = test_article()
        
        res = self._post_articles(a)
        self.assertEqual(set(res.keys()), {'id'}) # POST should only return IDs
        
        res = self._get_article(aid=res['id'])
        self.assertEqual(res["title"], a['title'])
        self.assertEqual(toolkit.read_date(res["date"]), toolkit.read_date(a['date']))
        self.assertNotIn("text", res.keys())
        self.assertIsNotNone(res["hash"])
        
        res = self._get_article(aid=res['id'], text=True)
        self.assertEqual(res["text"], a['text'])

        res = self._get_articles()["results"]
        self.assertEqual(len(res), 1)


    @amcattest.use_elastic
    def test_post_properties(self):
        a = test_article(foo='bar')
        res = self._post_articles(a)

        
        self.assertEqual(set(amcates.ES().query_ids(filters={"foo": "bar"})), {res["id"]})

        doc = amcates.ES().get(id=res['id'])
        self.assertEqual(doc['foo'], 'bar')
        
        db = self._get_article(aid=res['id'])
        self.assertEqual(db['foo'], 'bar')

        
    @amcattest.use_elastic
    def test_post_multiple(self):

        a1, a2 = [test_article() for _ in [1,2]]

        result = self._post_articles([a1,a2])
        self.assertEqual(2, len(result))
        self.assertEqual(set(result[0].keys()), {'id'}) # POST should only return IDs

        arts = self._get_articles()['results']
        self.assertEqual({a['title'] for a in arts}, {a1['title'], a2['title']})
        self.assertNotIn("text", arts[0].keys())

        arts = self._get_articles(text=True)['results']
        self.assertEqual({a['text'] for a in arts}, {a1['text'], a2['text']})
        
        arts = [Article.objects.get(pk=a["id"]) for a in result]
        self.assertEqual(arts[0].title, a1['title'])
        self.assertEqual(arts[1].title, a2['title'])
        
        # Are the articles added to the index?
        amcates.ES().flush()
        self.assertEqual(len(set(amcates.ES().query_ids(filters={"sets": self.aset.id}))), 2)
        
    @amcattest.use_elastic
    def test_post_id(self):
        a = amcattest.create_test_article()
        print(Article.objects.get(pk=a.id))
        result = self._post_articles({"id": a.id})
        self.assertEqual(set(amcates.ES().query_ids(filters={"sets": self.aset.id})), {a.id})

        a2 = amcattest.create_test_article()
        result = self._post_articles([{"id": a.id}, {"id": a2.id}])
        self.assertEqual(set(amcates.ES().query_ids(filters={"sets": self.aset.id})), {a.id, a2.id})

        # does it also work if we just post the ids?
        self.setUp_set()
        result = self._post_articles(a.id)
        self.assertEqual(set(amcates.ES().query_ids(filters={"sets": self.aset.id})), {a.id})
        result = self._post_articles([a.id, a2.id])
        self.assertEqual(set(amcates.ES().query_ids(filters={"sets": self.aset.id})), {a.id, a2.id})

        
    @amcattest.use_elastic
    def test_dupe(self):
        """Test whether deduplication works"""
        title = 'testartikel'
        a = test_article(title=title)
        aid1 = self._post_articles(a)['id']
        self.setUp_set()
        aid2 = self._post_articles(a)['id']
        amcates.ES().flush()
        # are the resulting ids identical?
        self.assertEqual(aid1, aid2)
        # is it added to elastic for this set?
        self.assertEqual(set(amcates.ES().query_ids(filters={'sets':self.aset.id})), {aid1})
        # is it not added (ie we only have one article with this title)
        self.assertEqual(set(amcates.ES().query_ids(filters={'title': a['title']})), {aid1})

        
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
        
        result, = self._post_articles([test_article(parent=article.id)])
        new_article = Article.objects.get(id=result["id"])
        self.assertEqual(article, new_article.parent)

        # test posting existing uuid
        result, = self._post_articles([test_article(parent=article.uuid)])
        new_article = Article.objects.get(id=result["id"])
        self.assertEqual(article, new_article.parent)

        # test posting article and child with uuid
        p = test_article(uuid=str(uuid4()))
        c = test_article(parent=p['uuid'])
        result = self._post_articles([p,c])
        pa, ca = [Article.objects.get(pk=a["id"]) for a in result]
        self.assertEqual(pa, ca.parent)
        
        
    def test_permissions(self):
        from amcat.models import Role, ProjectRole
        metareader = Role.objects.get(label='metareader', projectlevel=True)
        reader = Role.objects.get(label='reader', projectlevel=True)

        p1 = amcattest.create_test_project(guest_role=None)
        p2 = amcattest.create_test_project(guest_role=metareader)
        p3 = amcattest.create_test_project(guest_role=reader)
        p4 = amcattest.create_test_project(guest_role=reader)

        s1 = amcattest.create_test_set(project=p1)
        p2.articlesets.add(s1)
        p3.articlesets.add(s1)
        s2 = amcattest.create_test_set(project=p2)

        
        # anonymous user shoud be able to read articles on p2 and p3
        self._get_articles(projectid=p3.id, setid=s1.id, expected_status=200, as_user=None)
        self._get_articles(projectid=p2.id, setid=s1.id, expected_status=200, as_user=None)
        self._get_articles(projectid=p1.id, setid=s1.id, expected_status=401, as_user=None)

        
        # anonymous user shoud be able to read articles on p3 only
        self._get_articles(projectid=p3.id, setid=s1.id, expected_status=200, as_user=None, text=True)
        self._get_articles(projectid=p2.id, setid=s1.id, expected_status=401, as_user=None, text=True)
        self._get_articles(projectid=p1.id, setid=s1.id, expected_status=401, as_user=None, text=True)

        # it is illegal to view an articleset through a project it is not a member of
        self._get_articles(projectid=p4.id, setid=s1.id, expected_status=404)

        # owner and project readers can access project and (linked) article sets
        u = p1.owner
        self._get_articles(projectid=p1.id, setid=s1.id, expected_status=200, as_user=u)
        self._get_articles(projectid=p2.id, setid=s1.id, expected_status=200, as_user=p2.owner)
        ProjectRole.objects.create(project=p2, user=u, role=reader)
        self._get_articles(projectid=p2.id, setid=s1.id, expected_status=200, as_user=u)

        # User u should be able to add articles to set 1 via p1, but not via p2 or to s2
        body = test_article()
        self._post_articles(body, projectid=p1.id, setid=s1.id, as_user=u, expected_status=201)
        self._post_articles(body, projectid=p2.id, setid=s2.id, as_user=u, expected_status=403)

        # You can't modify a linked resource
        self._post_articles(body, projectid=p2.id, setid=s1.id, as_user=u, expected_status=403)
        self._post_articles(body, projectid=p2.id, setid=s1.id, as_user=p2.owner, expected_status=403)


        # You can only add articles to an articleset if you can (1) modify the set, and (2) read the articles
        a = amcattest.create_test_article(articleset=s1)
        
        self._post_articles(a.id, projectid=p2.id, setid=s2.id, as_user=p2.owner, expected_status=201)
        self._post_articles(a.id, projectid=p2.id, setid=s2.id, as_user=u, expected_status=403) # cannot write

        # project owner 4 can read s1 (via p3), so it's ok
        s4 = amcattest.create_test_set(project=p4)
        a1 = amcattest.create_test_article(articleset=s1)
        self._post_articles(a1.id, projectid=p4.id, setid=s4.id, as_user=p4.owner, expected_status=201) 

        # but he can't read s2:
        a2 = amcattest.create_test_article(articleset=s2)
        self._post_articles(a2.id, projectid=p4.id, setid=s4.id, as_user=p4.owner, expected_status=403) 

        # so he also can't post both of them:
        self._post_articles([a1.id, a2.id], projectid=p4.id, setid=s4.id, as_user=p4.owner, expected_status=403) 

        # unless he gets read access to project 2
        ProjectRole.objects.create(project=p2, user=p4.owner, role=reader)
        self._post_articles([a1.id, a2.id], projectid=p4.id, setid=s4.id, as_user=p4.owner, expected_status=201) 
        

