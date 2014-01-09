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
import collections
import itertools
import logging
import memcache

from django.db.models import Q
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from amcat.models import Medium, to_medium_ids
from amcat.models.amcat import AmCAT
from amcat.tools.toolkit import splitlist
from amcat.tools.model import AmcatModel
from amcat.tools import amcates
from amcat.tools.djangotoolkit import get_or_create, distinct_args
from amcat.models.article import Article
from amcat.tools.progress import NullMonitor
log = logging.getLogger(__name__)


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
    articles = models.ManyToManyField(Article, related_name="articlesets_set")

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

    def add_articles(self, articles, add_to_index=True, monitor=NullMonitor()):
        """
        Add the given articles to this article set
        """

        articles = {(art if type(art) is int else art.id) for art in articles}
        to_add = articles - self.get_article_ids()
        # check that all articles exist:
        to_add = Article.objects.filter(pk__in=to_add).values_list("pk", flat=True)
        monitor.update(10, "{n} articles need to be added".format(n=len(to_add)))
        
        if not to_add:
            return
        # add to database
        ArticleSetArticle.objects.bulk_create(
            [ArticleSetArticle(articleset=self, article_id=artid) for artid in to_add]
        )
        monitor.update(20, "{n} articles added in database, adding to index".format(n=len(to_add)))
                
        if add_to_index:
            amcates.ES().add_to_set(self.id, to_add, monitor=monitor)

    def add(self, *articles):
        """add(*a) is an alias for add_articles(a)"""
        self.add_articles(articles)
            
    def remove_articles(self, articles, remove_from_index=True):
        """
        Add the given articles to this article set
        If refresh or deduplicate are True, schedule a new celery task to do this
        """
        ArticleSetArticle.objects.filter(articleset=self, article__in=articles).delete()
        
        if remove_from_index:
            to_remove = {(art if type(art) is int else art.id) for art in articles}
            amcates.ES().remove_from_set(self.id, to_remove)

    def get_article_ids(self):
        """
        Return the sequence of ids of articles in this set.
        This is an optimized form of 'return [a.id for a in self.articles.all()]'
        """
        from django.db import connection
        sql = str(ArticleSet.articles.through.objects.filter(articleset=self).values("article_id").query)
        cursor = connection.cursor()
        cursor.execute(sql)
        result = {aid for (aid,) in cursor.fetchall()}
        cursor.close() # no idea if it's needed, but Martijn told me to do it
        return result

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

    @classmethod
    def get_unique_name(cls, project, name):
        """Return a 'name [(n)]' that is unique in this project"""
        name2 = name
        for i in itertools.count():
            if not ArticleSet.objects.filter(project=project, name=name2).exists():
                return name2
            name2 = "{name} {i}".format(**locals())

    @classmethod
    def create_set(cls, project, name, articles=None):
        aset = cls.objects.create(project=project, name=cls.get_unique_name(project, name))
        if articles:
            aset.add_articles(articles)
        return aset

# Legacy
ArticleSetArticle = ArticleSet.articles.through

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest
from django.test import skipUnlessDBFeature

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
        



