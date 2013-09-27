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

"""ORM Module representing projects"""

from __future__ import unicode_literals, print_function, absolute_import

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Q
from django.core.cache import cache, backends
from django.db.models.query import QuerySet
import memcache
from amcat.models import Medium

from amcat.tools.model import AmcatModel
from amcat.models.coding.codebook import Codebook
from amcat.models.coding.codingschema import CodingSchema
from amcat.models.article import Article
from amcat.models.articleset import ArticleSetArticle, ArticleSet

ROLEID_PROJECT_READER = 11
LITTER_PROJECT_ID = 1

MEDIUM_CACHE_PREFIX = "project_{project.id}_mediums"

import logging; log = logging.getLogger(__name__)

def to_medium_ids(mediums):
    """
    Convert argument to medium ids

    @param mediums: mediums to be processed
    @type mediums: QuerySet | Medium | iterable of Mediums
    @return: iterable of medium ids
    """
    if isinstance(mediums, Medium):
        return (mediums.id,)

    if isinstance(mediums, QuerySet):
        return mediums.values_list("id", flat=True)

    return (m.id for m in mediums)


class Project(AmcatModel):
    """Model for table projects.

    Projects are the main organizing unit in AmCAT. Most other objects are
    contained within a project: articles, sets, codingjobs etc.

    Projects have users in different roles. For most authorisation questions,
    AmCAT uses the role of the user in the project that an object is contained in
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='project_id', editable=False)

    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200, null=True)

    insert_date = models.DateTimeField(db_column='insertdate', auto_now_add=True)
    owner = models.ForeignKey(User, db_column='owner_id')

    insert_user = models.ForeignKey(User, db_column='insertuser_id',
                                    related_name='inserted_project',
                                    editable=False)

    guest_role = models.ForeignKey("amcat.Role", default=ROLEID_PROJECT_READER, null=True)

    active = models.BooleanField(default=True)
    index_default = models.BooleanField(default=True)

    # Coding fields
    codingschemas = models.ManyToManyField("amcat.CodingSchema", related_name="projects_set")
    codebooks = models.ManyToManyField("amcat.Codebook", related_name="projects_set")
    articlesets = models.ManyToManyField("amcat.ArticleSet", related_name="projects_set")
    favourite_articlesets = models.ManyToManyField("amcat.articleset", related_name="favourite_of_projects")

    def cache_mediums(self, force=False):
        """
        Warm cache mediums for this project. Since we can't realistically count the amount
        of articles for each medium, we do not support automatic cache invalidation. This
        means that get_mediums() can return false positives (but never false negatives).

        @param force: override current cache (if any)
        @type force: bool
        """
        if cache.get(self._cache_key) is not None and not force:
            log.info("Cache for project {self.id} already filled. Skipping.".format(**locals()))
            return
        cache.set(self._cache_key, tuple(self._get_mediums().values_list("id", flat=True)))

    def get_mediums(self):
        """
        Returns mediums and (if possible) uses cache.

        @type return: QuerySet
        @param return: Mediums linked to this project
        """
        mediums_ids = cache.get(self._cache_key)
        if mediums_ids is None:
            log.warning("Medium cache for project {self.id} not set!".format(**locals()))
            return self._get_mediums()
        return Medium.objects.filter(id__in=mediums_ids)

    def add_to_mediums_cache(self, mediums):
        """
        Adds given mediums to cache.

        @param mediums: mediums to be added
        @type mediums: QuerySet | Medium | iterable of Mediums
        """
        key = cache.make_key(self._cache_key)
        ids = tuple(to_medium_ids(mediums))

        # Check whether we're running memcached
        client = cache._cache
        if not isinstance(client, memcache.Client):
            raise ImproperlyConfigured("To guarantee thread-safety, we need memcached as caching backend.")

        if client.get(key) is None:
            raise ValueError("Cache not yet initialised.")

        # Enable cas (disabled by default..)
        client.cache_cas = True

        # Apply compare and set pattern to prevent race conditions
        while True:
            _ids = client.gets(key)
            if client.cas(key, tuple(set(_ids + ids))):
                break

    @property
    def _cache_key(self):
        """Returns the key of the cache for cache backends."""
        return MEDIUM_CACHE_PREFIX.format(project=self).encode("UTF-8")

    def _invalidate_mediums_cache(self):
        cache.set(self._cache_key, None)

    def _get_mediums(self):
        """
        Returns mediums but does not use cache.

        @type return: QuerySet
        @param return: Mediums linked to this project
        """
        return Medium.objects.only("id").filter(
            article__articlesetarticle__articleset__in=self.all_articlesets(distinct=True)
        )


    def get_codingschemas(self):
        """
        Return all codingschemas connected to this project. This returns codingschemas
        owned by it and linked to it.
        """
        return CodingSchema.objects.filter(Q(projects_set=self)|Q(project=self)).distinct()

    def get_codebooks(self):
        """
        Return all codebooks connected to this project. This returns codebooks 
        owned by it and linked to it.
        """
        return Codebook.objects.filter(Q(projects_set=self)|Q(project=self)).distinct()
    
    def can_read(self, user):
        return (self in user.get_profile().projects
                or user.get_profile().haspriv('view_all_projects')
                or self.guest_role is not None)

    @property
    def users(self):
        """Get a list of all users with some role in this project"""
        return (r.user for r in self.projectrole_set.all())

    def all_articlesets(self, distinct=True):
        """
        Get a set of articlesets either owned by this project or
        contained in a set owned by this project
        """
        sets = ArticleSet.objects.filter(Q(project=self)|Q(projects_set=self))
        if distinct: return sets.distinct()
        return sets

    def all_articles(self):
        """
        Get a set of articles either owned by this project
        or contained in a set owned by this project
        """
        return Article.objects.filter(Q(articlesets_set__project=self)|Q(project=self)).distinct()
            
    def get_all_article_ids(self):
        """
        Get a sequence of article ids either owned by this project
        or contained in a set owned by this project
        """
        for a in Article.objects.filter(project=self).only("id"):
            yield a.id
        for asa in ArticleSetArticle.objects.filter(articleset__project=self):
            yield asa.article_id
        
    class Meta():
        db_table = 'projects'
        app_label = 'amcat'
        ordering = ('name',)

    def save(self, *args, **kargs):
        if self.insert_user_id is None:
            # Import at top causes a circular import, unfortunately
            from amcatnavigator.utils.auth import get_request

            # No insert user is set, try to retrieve it
            req = get_request()
            if req is not None:
                self.insert_user_id = req.user.id

        super(Project, self).save(*args, **kargs)


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestProject(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create a project and access its attributes?"""
        p = amcattest.create_test_project(name="Test")
        self.assertEqual(p.name, "Test")

        
    def test_all_articles(self):
        """Does getting all articles work?"""
        from django.db.models.query import QuerySet

        p1, p2 = [amcattest.create_test_project() for _x in [1,2]]
        a1, a2 = [amcattest.create_test_article(project=p) for p in [p1, p2]]
        self.assertEqual(set(p1.get_all_article_ids()), set([a1.id]))
        self.assertEqual(set(p1.all_articles()), set([a1]))
        
        s = amcattest.create_test_set(project=p1)
        self.assertEqual(set(p1.get_all_article_ids()), set([a1.id]))
        self.assertEqual(set(p1.all_articles()), set([a1]))
        s.add(a2)
        self.assertEqual(set(p1.get_all_article_ids()), set([a1.id, a2.id]))
        self.assertEqual(set(p1.all_articles()), set([a1, a2]))
        self.assertTrue(isinstance(p1.all_articles(), QuerySet))

    def test_all_articlesets(self):
        """Does getting all articlesets work?"""
        from django.db.models.query import QuerySet

        p1, p2 = [amcattest.create_test_project() for _x in [1,2]]
        a1 = amcattest.create_test_set(5, project=p1)
        a2 = amcattest.create_test_set(5, project=p2)

        self.assertEqual(set([a1]), set(p1.all_articlesets()))
        p1.articlesets.add(a2)
        self.assertEqual({a1, a2}, set(p1.all_articlesets()))
        self.assertTrue(isinstance(p1.all_articlesets(), QuerySet))


    def test_get_schemas(self):
        """Does get_schemas give the right results in the face of multiply imported schemas??"""
        p = amcattest.create_test_project()
        p2 = amcattest.create_test_project()
        p3 = amcattest.create_test_project()
        from django import forms
        cs = amcattest.create_test_schema(project=p)
        p.codingschemas.add(cs)
        p2.codingschemas.add(cs)
        class TestForm(forms.Form):
            c = forms.ModelChoiceField(queryset=p.get_codingschemas())
        
        self.assertEqual(len(p.get_codingschemas().filter(pk=cs.id)), 1)
        self.assertEqual(len(p2.get_codingschemas().filter(pk=cs.id)), 1)
        self.assertEqual(len(p3.get_codingschemas().filter(pk=cs.id)), 0)

    def test_to_medium_ids(self):
        m1, m2 = amcattest.create_test_medium(), amcattest.create_test_medium()
        self.assertEqual(set(to_medium_ids(m1)), {m1.id,})
        self.assertEqual(set(to_medium_ids([m1,m2])), {m1.id, m2.id})
        self.assertEqual(set(to_medium_ids(Medium.objects.filter(id__in=[m1.id, m2.id]))), {m1.id, m2.id})

    def test_cache_mediums(self):
        project = amcattest.create_test_project()
        project.cache_mediums()

        # Does cache backend work in test environment?
        from django.core.cache import cache
        cache.set("TEST_KEY", 1)
        self.assertEqual(cache.get("TEST_KEY"), 1)

        # Test whether cache is really used
        self.assertEquals([], list(project.get_mediums()))
        aset = amcattest.create_test_set(10, project=project)
        self.assertEquals([], list(project.get_mediums()))
        project.cache_mediums()
        self.assertEquals([], list(project.get_mediums()))
        project.cache_mediums(force=True)
        self.assertEquals({a.medium for a in aset.articles.all()}, set(project.get_mediums()))


    def test_add_to_mediums_cache(self):
        cache.clear()
        project = amcattest.create_test_project()

        Medium.objects.bulk_create([Medium(name="adfqwe" + str(i)) for i in range(100)])
        mediums = Medium.objects.filter(name__in=["adfqwe" + str(i) for i in range(100)])
        self.assertEqual(len(mediums), 100)

        # Must raise error when cache not initialised
        self.assertRaises(ValueError, project.add_to_mediums_cache, [])

        # Test if medium really added
        project.cache_mediums()
        project.add_to_mediums_cache(mediums[0])
        self.assertEqual(set(project.get_mediums()), {mediums[0],})

        # Test concurrency
        project = amcattest.create_test_project()
        project.cache_mediums()

        import multiprocessing.dummy
        p = multiprocessing.dummy.Pool(10)
        p.map(project.add_to_mediums_cache, mediums)
        self.assertEqual(set(project.get_mediums()), set(mediums))

        # Test adding multiple at once
        project = amcattest.create_test_project()
        project.cache_mediums()
        project.add_to_mediums_cache(mediums[0:2])
        self.assertEqual(set(project.get_mediums()), set(mediums[0:2]))
