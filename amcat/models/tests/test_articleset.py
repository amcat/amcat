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
from amcat.models import CodedArticle, Article, ArticleSet

from amcat.tools import amcattest
from amcat.tools.amcates import ES

import elasticsearch
from amcat.tools.progress import ProgressMonitor


class TestArticleSet(amcattest.AmCATTestCase):

    def test_create(self):
        """Can we create a set with some articles and retrieve the articles?"""
        s = amcattest.create_test_set()
        i = 7
        for _x in range(i):
            s.add(amcattest.create_test_article())
        self.assertEqual(i, len(s.articles.all()))

    @amcattest.use_elastic
    def test_add(self):
        """Can we create a set with some articles and retrieve the articles?"""
        s = amcattest.create_test_set()
        arts = [amcattest.create_test_article() for _x in range(10)]
        s.add_articles(arts[:5])
        self.assertEqual(5, len(s.articles.all()))
        s.add_articles(arts)
        self.assertEqual(set(arts), set(s.articles.all()))

    @amcattest.use_elastic
    def test_add_many(self):
        """Can we add a large number of articles from one set to another?"""
        s = amcattest.create_test_set()
        s2 = amcattest.create_test_set()
        p = amcattest.create_test_project()

        arts = [amcattest.create_test_article(project=p, create=False) for _x in range(1213)]
        Article.create_articles(arts, s)
        ES().flush()
        self.assertEqual(len(arts), s.get_count())
        s2.add_articles(arts))
        ES().flush()
        self.assertEqual(len(arts), s2.get_count())
        print(s2.get_count())

    @amcattest.use_elastic
    def test_add_codedarticles(self):
        """Does add() also update codingjobs?"""
        cj = amcattest.create_test_job(3)
        a1 = amcattest.create_test_article()

        self.assertEqual(3, cj.articleset.articles.all().count())
        self.assertEqual(3, CodedArticle.objects.filter(codingjob=cj).count())

        cj.articleset.add_articles([a1])
        self.assertEqual(4, cj.articleset.articles.all().count())
        self.assertEqual(4, CodedArticle.objects.filter(codingjob=cj).count())

    @amcattest.use_elastic
    def test_get_article_ids(self):
        aset = amcattest.create_test_set(10)

        ES().flush()

        self.assertEqual(set(aset.articles.all().values_list("id", flat=True)), aset.get_article_ids())
        self.assertEqual(set(aset.articles.all().values_list("id", flat=True)), aset.get_article_ids(use_elastic=True))

    @amcattest.use_elastic
    def test_delete(self):
        s = amcattest.create_test_set()
        sid = s.id
        s2 = amcattest.create_test_set()
        arts = [amcattest.create_test_article() for _x in range(10)]
        s.add_articles(arts[:8])
        s2.add_articles(arts[6:])
        ES().flush()
        s.delete()
        ES().flush()
        # articleset and articles only in that set are deleted
        self.assertRaises(ArticleSet.DoesNotExist, ArticleSet.objects.get, pk=sid)
        self.assertRaises(Article.DoesNotExist, Article.objects.get, pk=arts[0].id)
        # shared articles are not deleted
        self.assertEqual(Article.objects.get(pk=arts[6].id).id, arts[6].id)
        self.assertEqual(set(s2.articles.values_list("pk", flat=True)),
                         {a.id for a in arts[6:]})
        # index is updated
        self.assertEqual(ES().count(filters={"sets": sid}), 0)
        self.assertEqual(ES().count(filters={"sets": s2.id}), 4)
        self.assertRaises(elasticsearch.NotFoundError, ES().get, arts[0].id)
        self.assertEqual(ES().get(arts[6].id)['id'], arts[6].id)
