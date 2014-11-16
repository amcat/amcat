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

"""
Model module for Article Sets. A Set is a generic collection of articles,
either created manually or as a result of importing articles or assigning
coding jobs.
"""

from __future__ import unicode_literals, print_function, absolute_import
import itertools
import json
import logging

from django.db import models
from django.db import connection

from amcat.models.medium import Medium
from amcat.models.coding.codedarticle import CodedArticle
from amcat.models.amcat import AmCAT
from amcat.tools.model import AmcatModel
from amcat.tools import amcates
from amcat.models.article import Article
from amcat.tools.progress import NullMonitor, ProgressMonitor
from amcat.tools.amcates import ES

log = logging.getLogger(__name__)
stats_log = logging.getLogger("statistics:" + __name__)


def create_new_articleset(name, project):
    """Create a new articleset based on name. If articleset exists add postfix number to make articleset name unique."""
    name=ArticleSet.get_unique_name(project, name)
    return ArticleSet.objects.create(project=project, name=name)

class ArticleSet(AmcatModel):
    """
    Model for the sets table. A set is part of a project and contains articles.
    It can also be seen as a 'tag' for articles.
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='articleset_id')

    name = models.CharField(max_length=200)
    project = models.ForeignKey("amcat.Project", related_name='articlesets_set')
    articles = models.ManyToManyField("amcat.Article", related_name="articlesets_set")

    provenance = models.TextField(null=True)

    class Meta():
        app_label = 'amcat'
        db_table = 'articlesets'
        ordering = ['name']

    def get_mediums(self):
        """
        Return a sequence of Medium object used in this set
        """
        from amcat.tools.amcates import ES
        medium_ids = ES().list_media(filters=dict(sets=self.id))
        return Medium.objects.filter(id__in=medium_ids)

    def get_count(self):
        """
        Return the number of articles according to elastic search
        """
        from amcat.tools.amcates import ES
        return ES().count(filters={"sets": self.id})

    def add_articles(self, articles, add_to_index=True, monitor=NullMonitor()):
        """
        Add the given articles to this article set. Implementation is exists of three parts:

          1. Adding ArticleSetArticle objects
          2. Adding CodedArticle objects
          3. Updating index

        @param articles: articles to be removed
        @type articles: iterable with indexing of integers or Article objects

        @param add_to_index: notify elasticsearch of changes
        @type add_to_index: bool
        """
        articles = {(art if type(art) is int else art.id) for art in articles}
        to_add = articles - self.get_article_ids()
        # Only use articles that exist
        to_add = list(Article.exists(to_add))

        monitor.update(10, "{n} articles need to be added".format(n=len(to_add)))
        ArticleSetArticle.objects.bulk_create(
            [ArticleSetArticle(articleset=self, article_id=artid) for artid in to_add],
            batch_size=100,
        )

        monitor.update(20, "{n} articleset articles added to database, adding to codingjobs".format(n=len(to_add)))
        cjarts = [CodedArticle(codingjob=c, article_id=a) for c, a in itertools.product(self.codingjob_set.all(), to_add)]
        CodedArticle.objects.bulk_create(cjarts)

        monitor.update(30, "{n} articles added to codingjobs, adding to index".format(n=len(cjarts)))
        if add_to_index:
            amcates.ES().add_to_set(self.id, to_add, monitor=monitor)

    def add(self, *articles):
        """add(*a) is an alias for add_articles(a)"""
        self.add_articles(articles)

    def remove_articles(self, articles, remove_from_index=True):
        """
        Remove article from this articleset. Also removes CodedArticles (from codingjobs) and updates
        index if `remove_from_index` is True.

        @param articles: articles to be removed
        @type articles: iterable with indexing of integers or Article objects

        @param remove_from_index: notify elasticsearch of changes
        @type remove_from_index: bool
        """
        ArticleSetArticle.objects.filter(articleset=self, article__in=articles).delete()
        CodedArticle.objects.filter(codingjob__articleset=self, article__in=articles).delete()

        if remove_from_index:
            to_remove = {(art if type(art) is int else art.id) for art in articles}
            amcates.ES().remove_from_set(self.id, to_remove)

    def get_article_ids(self, use_elastic=False):
        """
        Return the sequence of ids of articles in this set.
        This is an optimized form of 'return [a.id for a in self.articles.all()]'

        @rtype: set
        """
        if use_elastic:
            return self.get_article_ids_from_elastic()

        sql = str(ArticleSet.articles.through.objects.filter(articleset=self).values("article_id").query)
        cursor = connection.cursor()
        cursor.execute(sql)
        result = {aid for (aid,) in cursor.fetchall()}
        cursor.close() # no idea if it's needed, but Martijn told me to do it
        return result

    def get_article_ids_from_elastic(self):
        """
        Return the sequence of ids of articles in this set. As opposed to get_article_ids, this
        method uses elastic to fetch its data.

        @rtype: set
        """
        return set(ES().query_ids(filters={"sets" : [self.id]}))

    def refresh_index(self, full_refresh=False):
        """
        Make sure that the index for this set is up to date
        """
        from amcat.tools.amcates import ES
        ES().check_index()
        ES().synchronize_articleset(self, full_refresh=full_refresh)
        self.save()

    def save(self, *args, **kargs):
        new = not self.pk
        super(ArticleSet, self).save(*args, **kargs)

        if new:
            # new article set, add as fav to parent project
            # (I run parent first because I guess it needs a pk to add it, but didn't test whether
            #  this is needed...)
            self.project.favourite_articlesets.add(self)
            self.project.save()

            stats_log.info(json.dumps({
                "action": "articleset_added", "id": self.id,
                "name": self.name, "project_id": self.project_id,
                "project__name": self.project.name
            }))

    @classmethod
    def get_unique_name(cls, project, name):
        """Return a 'name [(n)]' that is unique in this project"""
        name2 = name
        for i in itertools.count():
            if not ArticleSet.objects.filter(project=project, name=name2).exists():
                return name2
            name2 = "{name} {i}".format(**locals())

    @classmethod
    def create_set(cls, project, name, articles=None, favourite=True):
        aset = cls.objects.create(project=project, name=cls.get_unique_name(project, name))
        if articles:
            aset.add_articles(articles)
        if not favourite:
            project.favourite_articlesets.remove(aset)
        return aset

# Legacy
ArticleSetArticle = ArticleSet.articles.through

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest


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


        # Are mediums cached?
        s.refresh_index()
        self.assertEqual(set(s.get_mediums()), {a.medium for a in arts})

    @amcattest.use_elastic
    def test_add_many(self):
        """Can we add a large number of articles from one set to another?"""
        s = amcattest.create_test_set()
        s2 = amcattest.create_test_set()
        m = amcattest.create_test_medium()
        p = amcattest.create_test_project()

        arts = [amcattest.create_test_article(project=p, medium=m, create=False) for _x in range(1213)]
        Article.create_articles(arts, s, create_id=True)
        ES().flush()
        self.assertEqual(len(arts), s.get_count())
        s2.add_articles(arts, monitor=ProgressMonitor())
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
    def test_get_mediums(self):
        from django.core.cache import cache
        cache.clear()
        AmCAT.enable_mediums_cache()

        aset = amcattest.create_test_set(0)
        media = [amcattest.create_test_medium(name="Test__"+str(i)) for i in range(10)]
        for m in media:
            aset.add(amcattest.create_test_article(medium=m))
        aset.refresh_index()

        # Test if medium really added
        self.assertEqual(set(aset.get_mediums()), set(media))

    @amcattest.use_elastic
    def test_get_article_ids(self):
        aset = amcattest.create_test_set(10)

        ES().flush()

        self.assertEqual(set(aset.articles.all().values_list("id", flat=True)), aset.get_article_ids())
        self.assertEqual(set(aset.articles.all().values_list("id", flat=True)), aset.get_article_ids(use_elastic=True))
