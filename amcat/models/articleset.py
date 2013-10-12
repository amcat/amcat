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
from amcat.tools.djangotoolkit import get_or_create
from amcat.models.article import Article

log = logging.getLogger(__name__)

MEDIUM_CACHE_KEY = "project_{articleset.id}_mediums"

def deduplicate(articles, compare):
    """
    Yield id's of duplicate articles. Articles in `compare` will be treated with a
    lower priority than those in `articles`, meaning they will be deleted first.

    @param articles: high-priority articles
    @type articles: iterator with tuples (id, md5)
    @param compare: low-priority articles
    @type compare: iterator with tuples(id, md5)
    @return: generator yielding duplicate articles
    """
    hashes = set()
    aids = set()

    # Build md5 -> id mapping, yield duplicates in `articles`
    for id, md5 in articles:
        if md5 in hashes:
            yield id
        else:
            aids.add(id)
            hashes.add(md5)

    # For all articles in compare, with a hash in hashes: yield id
    for id, md5 in compare:
        if md5 in hashes and not id in aids:
            yield id

def _get_hashes(articles, md5_query=None):
    return articles.distinct("id").extra({"md5":md5_query}).values_list("id", "md5")

def get_or_create_articleset(name, project):
    """
    Finds an articleset based on its name. If it does not exists, it creates
    one and returns that one instead.

    @type name: unicode
    @param name: name attribute of ArticleSet
    @type project: project.Project
    @param project: project attribute of ArticleSet
    @return: ArticleSet object or None if name is None
    """
    return get_or_create(ArticleSet, name=name, project=project) if name else None

def create_new_articleset(name, project):
    """Create a new articleset based on name. If articleset exists add postfix number to make articleset name unique."""
    name=ArticleSet.get_unique_name(project, name)
    return ArticleSet.objects.create(project=project, name=name) 

def _articles_to_ids(articles):
    """
    Convert given articles to article ids.

    @param articles: articles to convert
    @type articles: iterable with each type(object) in (int, Article)
    """
    for art in articles:
        yield art if type(art) is int else art.id

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

    indexed = models.BooleanField(default=None, null=False)
    index_dirty = models.BooleanField(default=True)
    needs_deduplication = models.BooleanField(default=True)
    
    class Meta():
        app_label = 'amcat'
        db_table = 'articlesets'
        ordering = ['name']

    def __init__(self, *args, **kargs):
        super(ArticleSet, self).__init__(*args, **kargs)
        # default value for indexed from project.
        # Check for project_id to prevent error on bare instantiation, e.g. for a form
        # TODO should we override create/save instead?
        if self.indexed is None and self.project_id is not None:
            self.indexed = self.project.index_default

    def get_medium_ids(self):
        """
        Returns medium ids used in this articleset from the index
        """
        from amcat.tools.amcates import ES
        return ES().list_media(filters=dict(sets=self.id))

    def get_mediums(self):
        """
        Returns mediums and (if possible) uses cache.

        @type return: QuerySet
        @param return: Mediums linked to this project
        """
        result =  Medium.objects.filter(id__in=self.get_medium_ids())
        return result

    @property
    def _cache_key(self):
        """Returns the key of the cache for cache backends."""
        return MEDIUM_CACHE_KEY.format(articleset=self).encode("UTF-8")

    def add(self, *articles):
        """Add the given articles to this article set"""
        return self.add_articles(articles)

    def add_articles(self, articles, set_dirty=True, deduplicate=False):
        """
        Add the given articles to this article set
        @param set_dirty: Set the index_dirty state of this set? (default=True)
        @param deduplicate: run this.deduplicate()
        @param cache_mediums: Add new mediums to cache
        """

        existing = set(aid for (aid,) in self.articles.values_list("id"))
        to_add = set(_articles_to_ids(articles)) - existing

        if not to_add:
            return
        
        ArticleSetArticle.objects.bulk_create(
            [ArticleSetArticle(articleset=self, article_id=artid) for artid in to_add]
        )

        to_add = Article.objects.filter(id__in=to_add)

        if deduplicate:
            self.deduplicate(compare=to_add, set_dirty=set_dirty)

        if set_dirty:
            self.index_dirty = True
            self.save()


    def remove(self, *articles):
        """Remove the given articles from this set"""
        ArticleSetArticle.objects.filter(articleset=self, article__in=articles).delete()
        self.index_dirty = True
        self.save()

    def _get_article_ids(self):
        """
        Get the ids of articles in this set. This is an optimized form of
        'return [a.id for a in self.articles.all()]'
        @return: a set of article ids (integers)
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
        ES().refresh_articleset_index(self, full_refresh=full_refresh)
        self.index_dirty = False
        self.save()
        
    @property
    def index_state(self):
        in_progress = []
        if self.indexed and self.index_dirty: in_progress.append("Indexing")
        if self.needs_deduplication: in_progress.append("Deduplication")
        if in_progress:
            return "{} in progress".format(", ".join(in_progress))
        else:
            return "Fully indexed"


    def fuzzy_deduplicate(self):
        raise NotImplementedError("Please use scripts/actions/deduplicate.py")

    def _deduplicate(self, compare, columns):
        """Yield id's of duplicates in this articleset"""
        md5_query = "MD5(ROW({})::TEXT)".format(",".join(columns))
        from amcat.tools.djangotoolkit import db_supports_distinct_on
        if db_supports_distinct_on():
            dates = compare.distinct("date").values_list("date", flat=True)
        else:
            dates = compare.distinct().values_list("date", flat=True)
            
        # Checking per date prevents loading whole articlesets at once
        for date in { d.date() for d in dates }:
            date_filter = Q(date__year=date.year, date__month=date.month, date__day=date.day)
            compare_articles = _get_hashes(compare.filter(date_filter), md5_query)
            articles = _get_hashes(self.articles.filter(date_filter), md5_query)

            for id in deduplicate(articles, compare_articles):
                yield id

    def deduplicate(self, compare=None, set_dirty=True, columns=("headline", "byline", "text", "date", "medium_id")):
        """
        Deduplicate using strict methods. The following properties must be exactly the same in
        order to match: headline, byline, text, medium and date. Of those columns, date is enforced
        by the implementation.

        @param compare: check only these articles for duplicates (useful when adding articles)
        @type compare: QuerySet or NoneType

        @param set_dirty: set index to dirty when set changed
        @type set_dirty: bool

        @param columns: columns to consider when comparing
        @type columns: iterable
        """
        compare = self.articles.all() if compare is None else compare
        remove = set(self._deduplicate(compare, columns))
        if remove: 
            self.articles.through.objects.filter(article__id__in=remove).delete()

            if set_dirty:
                self.index_dirty = True
        self.needs_deduplication = False
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

class TestArticleSet(amcattest.PolicyTestCase):
    @classmethod
    def setUpClass(cls):
        from django.conf import settings
        from amcat.tools import amcates
        cls.old_index = settings.ES_INDEX
        settings.ES_INDEX += "__unittest"
        amcates.ES().delete_index()
        amcates.ES().create_index()
        
    def test_create(self):
        """Can we create a set with some articles and retrieve the articles?"""       
        s = amcattest.create_test_set()
        i = 7
        for _x in range(i):
            s.add(amcattest.create_test_article())
        self.assertEqual(i, len(s.articles.all()))
        
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

        
    def test_dirty(self):
        """Is the dirty flag set correctly?"""
        p = amcattest.create_test_project(index_default=True)
        s = amcattest.create_test_set(project=p)
        self.assertEqual(s.indexed, True)
        self.assertEqual(s.index_dirty, True)
        s.index_dirty=False
        s.save()
        s.add(amcattest.create_test_article())
        self.assertEqual(s.index_dirty, True)
        s.refresh_index()
        self.assertEqual(s.index_dirty, False)

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
        

    def test_deduplicate(self):
        # add_articles should not default to removing duplicates
        set1 = amcattest.create_test_set(10)
        self.assertEqual(10, set1.articles.count())

        # All have different mediums, so no articles should be removed
        set1.deduplicate()
        self.assertEqual(10, set1.articles.count())

        # If we only considers dates, articles should be removed
        set1.deduplicate(columns=("date",))
        self.assertEqual(1, set1.articles.count())

        # Adding a duplicate should result in the oldest being kept
        a1 = set1.articles.all()[0]
        a2 = amcattest.create_test_article()
        set1.add(a2)
        set1.deduplicate(compare=Article.objects.filter(id=a2.id), columns=("date",))
        self.assertEqual(1, set1.articles.count())
        self.assertTrue(a1 in set1.articles.all())

        # Adding multiple duplicates
        a3, a4 = amcattest.create_test_article(), amcattest.create_test_article()
        a34 = Article.objects.filter(id__in=(a3.id, a4.id))
        set1.add(a3, a4)
        set1.deduplicate(compare=a34, columns=("date",))
        self.assertEqual(1, set1.articles.count())
        self.assertTrue(a1 in set1.articles.all())



