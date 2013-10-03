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
    articles = models.ManyToManyField(Article, through="amcat.ArticleSetArticle", related_name="articlesets_set")

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

    def add_to_mediums_cache(self, mediums):
        """
        Adds given mediums to cache.

        @rtype : NoneType
        @param mediums: mediums to be added
        @type mediums: QuerySet | Medium | iterable of Mediums | iterable of Medium ids
        """
        key = cache.make_key(self._cache_key)
        ids = tuple(to_medium_ids(mediums))

        # Check whether we're running memcached
        client = cache._cache
        if not isinstance(client, memcache.Client):
            raise ImproperlyConfigured("To guarantee thread-safety, we need memcached as caching backend.")

        # Enable cas (disabled by default..)
        client.cache_cas = True

        # Apply compare and set pattern to prevent race conditions
        while True:
            _ids = client.gets(key) or ()
            if client.cas(key, tuple(set(_ids + ids))):
                return set(_ids + ids)

    def clear_medium_cache(self):
        cache.set(self._cache_key, None)

    def cache_mediums(self):
        """
        Warm cache mediums for this articleset. Since we can't realistically count the amount
        of articles for each medium, we do not support automatic cache invalidation. This
        means that get_mediums() can return false positives (but never false negatives).

        @rtype: iterable with added medium id's
        """
        return self.add_to_mediums_cache(self._get_medium_ids())

    def _get_medium_ids(self):
        """
        Returns medium ids used in this articleset, but does not uses cache. May
        return duplicates.
        """
        return tuple(self.articles.all().values_list("medium__id", flat=True))

    def get_medium_ids(self):
        """
        Returns medium ids used in this articleset. Uses cache if enabled.
        """
        if not AmCAT.mediums_cache_enabled():
            log.warning("Medium cache not enabled. This function might be slow.".format(**locals()))
            mediums_ids = self._get_medium_ids()
        return cache.get(self._cache_key, ())

    def get_mediums(self):
        """
        Returns mediums and (if possible) uses cache.

        @type return: QuerySet
        @param return: Mediums linked to this project
        """
        return Medium.objects.filter(id__in=self.get_medium_ids())

    @property
    def _cache_key(self):
        """Returns the key of the cache for cache backends."""
        return MEDIUM_CACHE_KEY.format(articleset=self).encode("UTF-8")

    def add(self, *articles):
        """Add the given articles to this article set"""
        return self.add_articles(articles)

    def add_articles(self, articles, set_dirty=True, deduplicate=False, cache_mediums=True):
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

        if cache_mediums:
            self.add_to_mediums_cache(to_add.values_list("medium__id", flat=True))

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

    def _get_article_ids_solr(self, solr):
        """
        Get a list of article ids in this set according to solr. 
        @param solr: The amcatsolr.Solr object to use
        """
        return solr.query_ids("sets:{self.id}".format(**locals()))

    def reset_index(self, full_refresh=False, solr=None):
        """
        Set the index to dirty so it will be refreshed.
        @param full_refresh: if True, delete all existing information from the set
        @param solr: Optional amcatsolr.Solr object to use (e.g. for testing)
        """
        # lazy load to prevent import cycle
        from amcat.tools.amcatsolr import Solr
        if solr is None: solr = Solr()
        if full_refresh:
            solr_ids = self._get_article_ids_solr(solr=solr)
            for i, batch in enumerate(splitlist(solr_ids)):
                solr.delete_articles(batch)
        self.index_dirty=True
        self.save()
    
    def refresh_index(self, solr=None, full_refresh=False):
        """
        Make sure that the SOLR index for this set is up to date
        @param solr: Optional amcatsolr.Solr object to use (e.g. for testing)
        """
        # lazy load to prevent import cycle
        from amcat.tools.amcatsolr import Solr
        if solr is None: solr = Solr()
        log.debug("Getting SOLR ids")
        solr_ids = self._get_article_ids_solr(solr)
        log.debug("Getting DB ids")
        db_ids = set(id for (id,) in self.articles.all().values_list("id")) if self.indexed else set()
        to_remove = solr_ids - db_ids
        to_add = db_ids if full_refresh else  db_ids - solr_ids

        log.warn("Refreshing index, full_refresh={full_refresh}, |solr_ids|={nsolr}, |db_ids|={ndb}, "
                 "|to_add|={nta}, |to_remove|={ntr}"
                  .format(nsolr=len(solr_ids), ndb=len(db_ids), nta=len(to_add), ntr=len(to_remove),**locals()))
        
            
        for i, batch in enumerate(splitlist(to_remove)):
            solr.delete_articles(batch)
            log.debug("Removed batch {i}".format(**locals()))
        for i, batch in enumerate(splitlist(to_add, itemsperbatch=1000)):
            solr.add_articles(batch)
            log.debug("Added batch {i}".format(**locals()))

        self.index_dirty = False
        self.save()
        
    @property
    def index_state(self):
        in_progress = []
        if self.indexed and self.index_dirty: in_progress.append("Indexing")
        if self.needs_deduplication: in_progress.append("Deduplication")
        if in_progress:
            return "{} in progress".format(", ".join(in_progress))
        elif self.indexed:
            return "Fully indexed"
        else:
            return "Not indexed"

    def fuzzy_deduplicate(self):
        raise NotImplementedError("Please use scripts/actions/deduplicate.py")

    def _deduplicate(self, compare, columns):
        """Yield id's of duplicates in this articleset"""
        md5_query = "MD5(ROW({})::TEXT)".format(",".join(columns))
        dates = compare.distinct("date").values_list("date", flat=True)

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
        if not remove: return

        self.articles.through.objects.filter(article__id__in=remove).delete()

        if set_dirty:
            self.index_dirty = True
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
            
class ArticleSetArticle(AmcatModel):
    """
    ManyToMany table for article sets. An explicit model allows more prefeting in
    django queries and doesn't cost anything

    WVA: I believe this is no longer needed with the new prefetch_related, so
         we might be able to refactor this class away?
    """
    id = models.AutoField(primary_key=True, db_column='id')
    articleset = models.ForeignKey(ArticleSet)
    article = models.ForeignKey(Article)

    class Meta():
        app_label = 'amcat'
        db_table="articlesets_articles"
        unique_together = ('article', 'articleset')
    
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestArticleSet(amcattest.PolicyTestCase):
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
        self.assertEqual(set(s.get_mediums()), {a.medium for a in arts})

        
    def test_dirty(self):
        """Is the dirty flag set correctly?"""
        from amcat.tools.amcatsolr import TestDummySolr

        p = amcattest.create_test_project(index_default=True)
        s = amcattest.create_test_set(project=p)
        self.assertEqual(s.indexed, True)
        self.assertEqual(s.index_dirty, True)
        s.index_dirty=False
        s.save()
        s.add(amcattest.create_test_article())
        self.assertEqual(s.index_dirty, True)
        s.refresh_index(TestDummySolr())
        self.assertEqual(s.index_dirty, False)

    def clear_solr(self, solr):
        ids = set(solr.query_ids("*:*", rows=99999))
        solr.delete_articles(ids)

    def test_refresh_index(self):
        """Are added/removed articles added/removed from the index?"""
        if amcattest.skip_slow_tests():
            return

        from amcat.tools.amcatsolr import TestSolr

        with TestSolr() as solr:
            self.clear_solr(solr)
            s = amcattest.create_test_set(indexed=True)
            a = amcattest.create_test_article()
            
            s.add(a)
            self.assertEqual(set(), s._get_article_ids_solr(solr))
            s.refresh_index(solr)
            self.assertEqual({a.id}, s._get_article_ids_solr(solr))

            s.remove(a)
            self.assertEqual({a.id}, s._get_article_ids_solr(solr))
            s.refresh_index(solr)
            self.assertEqual(set(), s._get_article_ids_solr(solr))

            # test that if not set.indexed, it is not added to solr
            s = amcattest.create_test_set(indexed=False)
            s.add(a)
            s.refresh_index(solr)
            self.assertEqual(set(), s._get_article_ids_solr(solr))

            # test that remove from index works for larger sets
            s = amcattest.create_test_set(indexed=True)
            arts = [amcattest.create_test_article(medium=a.medium) for i in range(20)]
            s.add(*arts)
            
            s.refresh_index(solr)
            solr_ids = s._get_article_ids_solr(solr)
            self.assertEqual(set(solr_ids), {a.id for a in arts})

            s.remove(arts[0])
            s.remove(arts[-1])
            s.refresh_index(solr)
            solr_ids = s._get_article_ids_solr(solr)
            self.assertEqual(set(solr_ids), {a.id for a in arts[1:-1]})

            # test that changing an article's properties can be reindexed
            arts[1].medium = amcattest.create_test_medium()
            arts[1].save()

            query = "sets:{s.id} AND mediumid:{m}".format(m=arts[1].medium.id, **locals())
            self.assertEqual(set(solr.query_ids(query)), set()) # before refresh
            s.refresh_index(solr, full_refresh=True)
            self.assertEqual(set(solr.query_ids(query)), {arts[1].id}) # after refresh

    def test_cache_mediums(self):
        from django.core.cache import cache
        cache.clear()
        AmCAT.enable_mediums_cache()

        # Does cache backend work in test environment?
        aset = amcattest.create_test_set(0)
        arts = amcattest.create_test_set(10).articles.all()

        cache.set("TEST_KEY", 1)
        self.assertEqual(cache.get("TEST_KEY"), 1)

        # Test whether cache is really used
        self.assertEquals([], list(aset.get_mediums()))
        aset.add_to_mediums_cache(arts[0].medium)
        self.assertEquals({arts[0].medium}, set(aset.get_mediums()))
        aset.add_articles(arts)
        self.assertEquals({a.medium for a in arts}, set(aset.get_mediums()))


    def test_add_to_mediums_cache(self):
        from django.core.cache import cache
        cache.clear()
        AmCAT.enable_mediums_cache()

        aset = amcattest.create_test_set(0)
        Medium.objects.bulk_create([Medium(name="adfqwe" + str(i)) for i in range(50)])
        mediums = Medium.objects.filter(name__in=["adfqwe" + str(i) for i in range(50)])
        self.assertEqual(len(mediums), 50)

        # Test if medium really added
        aset.add_to_mediums_cache(mediums[0])
        self.assertEqual(set(aset.get_mediums()), {mediums[0],})

        # Test concurrency
        import multiprocessing.dummy
        p = multiprocessing.dummy.Pool(10)
        p.map(aset.add_to_mediums_cache, mediums)
        self.assertEqual(set(aset.get_mediums()), set(mediums))

        # Test adding multiple at once
        aset = amcattest.create_test_set()
        aset.add_to_mediums_cache(mediums[0:2])
        self.assertEqual(set(aset.get_mediums()), set(mediums[0:2]))

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



