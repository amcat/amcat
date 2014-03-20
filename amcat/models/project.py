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
from django.db import models
from django.db.models import Q
import itertools
from amcat.models import Medium, ProjectRole

from amcat.tools.model import AmcatModel
from amcat.models.coding.codebook import Codebook
from amcat.models.coding.codingschema import CodingSchema
from amcat.models.article import Article
from amcat.models.articleset import ArticleSetArticle, ArticleSet

ROLEID_PROJECT_READER = 11
LITTER_PROJECT_ID = 1

import logging; log = logging.getLogger(__name__)

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

    # Coding fields
    codingschemas = models.ManyToManyField("amcat.CodingSchema", related_name="projects_set")
    codebooks = models.ManyToManyField("amcat.Codebook", related_name="projects_set")
    articlesets = models.ManyToManyField("amcat.ArticleSet", related_name="projects_set")
    favourite_articlesets = models.ManyToManyField("amcat.articleset", related_name="favourite_of_projects")

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
        return itertools.chain(
            Article.objects.filter(project=self).values_list("id", flat=True),
            ArticleSetArticle.objects.filter(articleset__project=self).values_list("article__id", flat=True)
        )

    def get_mediums(self):
        from amcat.tools.amcates import ES
        sets = [s.id for s in self.all_articlesets()]
        if not sets: return Medium.objects.none()
        medium_ids = ES().list_media(filters=dict(sets=sets))
        return Medium.objects.filter(id__in=medium_ids)

    class Meta():
        db_table = 'projects'
        app_label = 'amcat'
        ordering = ('name',)

    def save(self, *args, **kargs):
        if self.insert_user_id is None:
            # Import at top causes a circular import, unfortunately
            from navigator.utils.auth import get_request

            # No insert user is set, try to retrieve it
            req = get_request()
            if req is not None:
                self.insert_user_id = req.user.id

        super(Project, self).save(*args, **kargs)

    def get_role_id(self, user=None):
        """
        Return the role id that this user has, by his own right or as guest
        If user is None, returns the guest role id
        """
        project_role = None
        guest_role = self.guest_role_id
        
        if user:
            try:
                project_role = self.projectrole_set.get(user=user).role_id
            except ProjectRole.DoesNotExist:
                pass

        # int > None is removed in python3, so avoid direct comparison
        if project_role is None: return guest_role
        if guest_role is None: return project_role
        return max(project_role, guest_role)


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestProject(amcattest.AmCATTestCase):
        
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

    @amcattest.use_elastic
    def test_get_mediums(self):
        set1 = amcattest.create_test_set(2)
        set2 = amcattest.create_test_set(2, project=set1.project)
        set3 = amcattest.create_test_set(2)
        [s.refresh_index() for s in [set1, set2, set3]]
        
        media = set(set1.project.get_mediums())
        self.assertEqual(
            set(set1.project.get_mediums()),
            { a.medium for a in set1.articles.all() } | { a.medium for a in set2.articles.all() }
        )

        # can we get_mediums on an empty project?
        self.assertEqual(list(amcattest.create_test_project().get_mediums()), [])

