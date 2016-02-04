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
import json
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from amcat.models import Article
from amcat.tools import amcattest, amcates
from uuid import uuid4
import datetime


def test_article_dict(**kwargs):
    if 'date' not in kwargs: kwargs['date'] = datetime.datetime.now().isoformat()
    if 'headline' not in kwargs: kwargs['headline'] = 'test headline {}'.format(uuid4())
    if 'text' not in kwargs: kwargs['text'] = 'test text {}'.format(uuid4())
    if 'medium' not in kwargs: kwargs['medium'] = 'test'
    return kwargs    

class TestArticleUploadView(APITestCase):
    def setUp(self):
        self.project = amcattest.create_test_project()
        self.aset = amcattest.create_test_set()
        self.user = self.project.owner
        self.url = reverse("api:article-upload") + "?format=json"
        self.url_set = reverse("api:articleset-article-upload",
                               kwargs=dict(project=self.project.id, articleset=self.aset.id)) + "?format=json"

    def _post(self, data, to_set=True, expected_status=201):
        response = self.client.post(self.url_set if to_set else self.url,
                                    content_type="application/json", data=json.dumps(data))
        self.assertEqual(response.status_code, expected_status,
                         "Status code {response.status_code}: {response.content}".format(**locals()))
        return json.loads(response.content)
            

    @amcattest.use_elastic
    def test_post(self):
        self.client.login(username=self.user.username, password="test", to_set=True)

        a1, a2, a3, a4 = [test_article_dict() for _ in [1,2,3,4]]
        a1['children'] = [a2]
        a2['children'] = [a3]
        
        result = self._post([a1,a4], to_set=True)

        self.assertEqual(4, len(result))

        arts = [Article.objects.get(pk=a["id"]) for a in result]

        print a
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
        
        result, = self._post([test_article_dict(parent=article.id)])
        new_article = Article.objects.get(id=result["id"])
        self.assertEqual(article, new_article.parent)

        # test posting existing uuid
        result, = self._post([test_article_dict(parent=article.uuid)])
        new_article = Article.objects.get(id=result["id"])
        self.assertEqual(article, new_article.parent)

        # test posting article and child with uuid
        p = test_article_dict(uuid=unicode(uuid4()))
        c = test_article_dict(parent=p['uuid'])
        result = self._post([p,c])
        pa, ca = [Article.objects.get(pk=a["id"]) for a in result]
        self.assertEqual(pa, ca.parent)
        
        
