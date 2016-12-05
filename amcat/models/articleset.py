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

import itertools
import json
import logging

from django.db import models
from django.db import connection

from amcat.models.coding.codedarticle import CodedArticle
from amcat.tools.model import AmcatModel
from amcat.tools import amcates, toolkit
from amcat.models.article import Article
from amcat.tools.progress import ProgressMonitor
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

    def add_articles(self, article_ids, add_to_index=True, monitor=None):
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
        (monitor or ProgressMonitor(total=1)).submonitor(total=4)

        article_ids = {(art if type(art) is int else art.id) for art in article_ids}

        # Only use articles that exist
        to_add = article_ids - self.get_article_ids()
        to_add = list(Article.exists(to_add))

        monitor.update(message="Adding {n} articles to {aset}..".format(n=len(to_add), aset=self))
        ArticleSetArticle.objects.bulk_create(
            [ArticleSetArticle(articleset=self, article_id=artid) for artid in to_add],
            batch_size=100,
        )

        monitor.update(message="{n} articleset articles added to database, adding to codingjobs..".format(n=len(to_add)))
        cjarts = [CodedArticle(codingjob=c, article_id=a) for c, a in itertools.product(self.codingjob_set.all(), to_add)]
        CodedArticle.objects.bulk_create(cjarts)

        if add_to_index:
            monitor.update(message="{n} articles added to codingjobs, adding to index".format(n=len(cjarts)))
            amcates.ES().add_to_set(self.id, to_add, monitor=monitor)
        else:
            monitor.update(2)

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
            # new articleset, add as fav to parent project
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
            amcates.ES().flush()
            amcates.ES().purge_orphans()

        log.warn("Deleting set (and articlesetarticle references)")
        super(ArticleSet, self).delete() # cascade deletes all article references
        log.warn("Done!")

# Legacy
ArticleSetArticle = ArticleSet.articles.through

