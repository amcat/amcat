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
codingjobs.
"""
import functools
import itertools
import json
import logging
from typing import Set, Iterable

import django_redis
import redis
from django import db
from django.db import connection
from django.db import models

from amcat.models.article import Article
from amcat.models.coding.codedarticle import CodedArticle
from amcat.tools import amcates, toolkit
from amcat.tools.amcates import ES
from amcat.tools.model import AmcatModel
from amcat.tools.progress import NullMonitor

log = logging.getLogger(__name__)
stats_log = logging.getLogger("statistics:" + __name__)


@functools.lru_cache()
def _get_property_cache_key(id):
    db_name = db.connections.databases['default']['NAME']
    return "{}.articleset.{}.properties".format(db_name, id)


def create_new_articleset(name, project):
    """Create a new articleset based on name. If articleset exists add postfix number to make articleset name unique."""
    name=ArticleSet.get_unique_name(project, name)
    return ArticleSet.objects.create(project=project, name=name)


def get_used_properties_by_articlesets(articlesets: Iterable["ArticleSet"]) -> Iterable[str]:
    """Returns properties used in given articlesets. May contain duplicates."""
    for articleset in articlesets:
        yield from articleset.get_used_properties()


class ArticleSet(AmcatModel):
    """
    Model for the sets table. A set is part of a project and contains articles.
    It can also be seen as a 'tag' for articles.
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='articleset_id')

    name = models.CharField(max_length=200)

    # This field only determines the Project that owns the ArticleSet. Membership is determined via the
    # ProjectArticleSet model, and is unrelated to this field. (i.e. an ArticleSet is not necessarily part
    # of the Project that owns it.)
    project = models.ForeignKey("amcat.Project", related_name='articlesets_set')
    articles = models.ManyToManyField("amcat.Article", related_name="articlesets_set")

    provenance = models.TextField(null=True)
    featured = models.BooleanField(default=False)

    class Meta():
        app_label = 'amcat'
        db_table = 'articlesets'
        ordering = ['name']


    def get_count(self):
        """
        Return the number of articles according to elastic search
        """
        from amcat.tools.amcates import ES
        return ES().count(filters={"sets": self.id})

    def add_articles(self, article_ids, add_to_index=True, add_to_codingjobs=True, monitor=NullMonitor()):
        """
        Add the given articles to this articleset. Implementation is exists of three parts:

          1. Adding ArticleSetArticle objects
          2. Adding CodedArticle objects
          3. Updating index

        @param article_ids: articles to be removed
        @type article_ids: iterable with indexing of integers or Article objects

        @param add_to_index: notify elasticsearch of changes
        @type add_to_index: bool
        """
        monitor = monitor.submonitor(total=4)

        article_ids = {(art if type(art) is int else art.id) for art in article_ids}

        # Only use articles that exist
        to_add = article_ids - self.get_article_ids()
        to_add = list(Article.exists(to_add))

        monitor.update(message="Adding {n} articles to {aset}..".format(n=len(to_add), aset=self))
        ArticleSetArticle.objects.bulk_create(
            [ArticleSetArticle(articleset=self, article_id=artid) for artid in to_add],
            batch_size=100,
        )

        if add_to_codingjobs:
            monitor.update(message="{n} articleset articles added to database, adding to codingjobs..".format(n=len(to_add)))
            cjarts = [CodedArticle(codingjob=c, article_id=a) for c, a in itertools.product(self.codingjob_set.all(), to_add)]
            CodedArticle.objects.bulk_create(cjarts)
            monitor.update(message="{n} articles added to codingjobs".format(n=len(cjarts)))

        if add_to_index:
            monitor.update(message="Adding {n} articles to index".format(n=len(to_add)))
            es = ES()
            es.add_to_set(self.id, to_add, monitor=monitor)
            es.refresh()  # We need to flush, or setting cache will fail
            # Add to property cache
            properties = ES().get_used_properties(article_ids=to_add)
            self._add_to_property_cache(properties)
        else:
            monitor.update(2)



    def get_used_properties(self) -> Set[str]:
        cache = django_redis.get_redis_connection()  # type: redis.client.StrictRedis
        properties = cache.smembers(_get_property_cache_key(self.id))

        if not properties:
            properties = self._refresh_property_cache()
        else:
            properties = {p.decode() for p in properties}

        return {p for p in properties if p}

    def _add_to_property_cache(self, properties: Iterable[str]) -> Set[str]:
        """Add properties to property cache"""
        properties = {p.encode() for p in properties}
        cache = django_redis.get_redis_connection()  # type: redis.client.StrictRedis
        cache.sadd(_get_property_cache_key(self.id), "", *properties)
        return {p.decode() for p in properties}

    def _reset_property_cache(self):
        """Completely discard property cache"""
        cache = django_redis.get_redis_connection()  # type: redis.client.StrictRedis
        cache.delete(_get_property_cache_key(self.id))

    @classmethod
    def _reset_all_property_caches(cls):
        """Resets all property caches from all articlesets for current database. Use this
        function with care, it runs O(n) with N being the number of keys in Redis."""
        cache = django_redis.get_redis_connection()  # type: redis.client.StrictRedis
        cache_key = _get_property_cache_key("*")
        cache_keys = cache.keys(cache_key)
        if cache_keys:
            cache.delete(*cache_keys)

    def _refresh_property_cache(self) -> Set[str]:
        """Discard property cache and recalculate properties"""
        from amcat.tools.amcates import ES
        es = ES()
        es.refresh()
        properties = es.get_used_properties([self.id])
        self._reset_property_cache()
        return self._add_to_property_cache(properties)

    def add(self, *articles):
        """add(*a) is an alias for add_articles(a)"""
        self.add_articles(articles)

    def remove_articles(self, articles, remove_from_index=True, monitor=NullMonitor()):
        """
        Remove article from this articleset. Also removes CodedArticles (from codingjobs) and updates
        index if `remove_from_index` is True.

        @param articles: articles to be removed
        @type articles: iterable with indexing of integers or Article objects

        @param remove_from_index: notify elasticsearch of changes
        @type remove_from_index: bool
        """
        monitor = monitor.submonitor(4)
        to_remove = {(art if type(art) is int else art.id) for art in articles}

        monitor.update(message="Deleting articles from database")
        ArticleSetArticle.objects.filter(articleset=self, article__in=articles).delete()

        monitor.update(message="Deleting coded articles from database")
        CodedArticle.objects.filter(codingjob__articleset=self, article__in=articles).delete()

        if remove_from_index:
            monitor.update(message="Deleting from index")
            amcates.ES().remove_from_set(self.id, to_remove)
        else:
            monitor.update()

        monitor.update(message="Deleting from cache")
        self._reset_property_cache()

    def get_article_ids(self, use_elastic=False) -> Set[int]:
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

        # Also make sure property cache checks out
        self._reset_property_cache()
        self._refresh_property_cache()

    def save(self, *args, **kargs):
        super(ArticleSet, self).save(*args, **kargs)
        pa, created = ProjectArticleSet.objects.get_or_create(project=self.project,
                                                              articleset=self,
                                                              defaults=dict(is_favourite=True))

        if created:
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
            ProjectArticleSet.objects.filter(project=project, articleset=aset).update(is_favourite=False)
        return aset

    def delete(self, purge_orphans=True):
        "Delete the articleset and all articles from index and db"
        # which articles are only in this set?
        # check per N articles
        
        log.warn("Getting all articles")

        aids = list(self.articles.values_list("pk", flat=True))
        todelete = set(aids)
        log.warn("Finding orphans in {} articles".format(len(aids)))
        for aids in toolkit.splitlist(aids, itemsperbatch=1000):
            x = set(ArticleSetArticle.objects.filter(article_id__in=aids).exclude(articleset=self)
                    .values_list("article_id", flat=True))
            todelete -= x
        log.warn("Removing {} orphans from DB".format(len(todelete)))
        #Article.objects.filter(pk__in=todelete).delete()
        for i, aids in enumerate(toolkit.splitlist(todelete, itemsperbatch=10000)):
            if i > 1:
                log.warn("... batch {i} (x10k)".format(**locals()))
            #Article.objects.filter(pk__in=aids)._raw_delete(Article.objects.db)
            Article.objects.filter(pk__in=aids).only("pk").delete()

        log.warn("Getting set membership from elastic")
        esaids = list(self.get_article_ids_from_elastic())
        if esaids:
            log.warn("Removing set membership from elastic ({} articles)".format(len(esaids)))
            amcates.ES().remove_from_set(self.id, esaids)

        if purge_orphans:
            amcates.ES().refresh()
            amcates.ES().purge_orphans()

        log.warn("Deleting set (and articlesetarticle references)")
        super(ArticleSet, self).delete() # cascade deletes all article references
        log.warn("Done!")

# Legacy
ArticleSetArticle = ArticleSet.articles.through


class ProjectArticleSet(AmcatModel):
    project = models.ForeignKey('amcat.Project', on_delete=models.CASCADE)
    articleset = models.ForeignKey('amcat.ArticleSet', on_delete=models.CASCADE)  # tests say this should cascade. I'm not convinced
    is_favourite = models.BooleanField()

    class Meta:
        app_label = 'amcat'
        db_table = "projects_articlesets"
        unique_together = ("project", "articleset")
