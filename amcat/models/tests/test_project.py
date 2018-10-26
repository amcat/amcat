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
from datetime import datetime

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from amcat.models import ROLE_PROJECT_READER, ROLE_PROJECT_METAREADER, Role, ROLE_PROJECT_WRITER, \
    ROLE_PROJECT_ADMIN, ProjectArticleSet
from amcat.models import RecentProject, User
from amcat.tools import amcattest
from django.db.models.query import QuerySet


class TestProject(amcattest.AmCATTestCase):
    def test_create(self):
        """Can we create a project and access its attributes?"""
        p = amcattest.create_test_project(name="Test")
        self.assertEqual(p.name, "Test")

    def test_has_role(self):
        metareader_role = Role.objects.get(id=ROLE_PROJECT_METAREADER)
        reader_role = Role.objects.get(id=ROLE_PROJECT_READER)
        writer_role = Role.objects.get(id=ROLE_PROJECT_WRITER)
        admin_role = Role.objects.get(id=ROLE_PROJECT_ADMIN)

        project = amcattest.create_test_project(guest_role=reader_role)
        admin = User.objects.first()
        anon = AnonymousUser()

        # Anonymous user has project role
        self.assertTrue(project.has_role(anon, metareader_role))
        self.assertTrue(project.has_role(anon, metareader_role.id))
        self.assertTrue(project.has_role(anon, metareader_role.label))

        self.assertTrue(project.has_role(anon, reader_role))
        self.assertTrue(project.has_role(anon, reader_role.id))
        self.assertTrue(project.has_role(anon, reader_role.label))

        self.assertFalse(project.has_role(anon, writer_role))
        self.assertFalse(project.has_role(anon, writer_role.id))
        self.assertFalse(project.has_role(anon, writer_role.label))

        self.assertFalse(project.has_role(anon, admin_role))
        self.assertFalse(project.has_role(anon, admin_role.id))
        self.assertFalse(project.has_role(anon, admin_role.label))

        # I think we tested string/object/id enough at this point :-)

        # Superuser is omnipotent
        superuser = amcattest.create_test_user()
        superuser.is_superuser = True
        superuser.save()
        self.assertTrue(project.has_role(superuser, metareader_role))
        self.assertTrue(project.has_role(superuser, reader_role))
        self.assertTrue(project.has_role(superuser, writer_role))
        self.assertTrue(project.has_role(superuser, admin_role))

        # Project admin as well
        self.assertTrue(project.has_role(admin, metareader_role))
        self.assertTrue(project.has_role(admin, reader_role))
        self.assertTrue(project.has_role(admin, writer_role))
        self.assertTrue(project.has_role(admin, admin_role))



    def test_all_articles(self):
        """Does getting all articles work?"""

        p1, p2 = [amcattest.create_test_project() for _x in [1,2]]
        a1, a2 = [amcattest.create_test_article(project=p) for p in [p1, p2]]
        self.assertEqual(set(p1.get_all_article_ids()), {a1.id})
        self.assertEqual(set(p1.all_articles()), {a1})

        s = amcattest.create_test_set(project=p1)
        self.assertEqual(set(p1.get_all_article_ids()), {a1.id})
        self.assertEqual(set(p1.all_articles()), {a1})
        s.add(a2)
        self.assertEqual(set(p1.get_all_article_ids()), {a1.id, a2.id})
        self.assertEqual(set(p1.all_articles()), {a1, a2})
        self.assertTrue(isinstance(p1.all_articles(), QuerySet))

    def test_all_articlesets(self):
        """Does getting all articlesets work?"""
        from django.db.models.query import QuerySet

        p1, p2 = [amcattest.create_test_project() for _x in [1,2]]
        a1 = amcattest.create_test_set(5, project=p1)
        a2 = amcattest.create_test_set(5, project=p2)

        self.assertEqual({a1}, set(p1.all_articlesets()))
        ProjectArticleSet.objects.create(project=p1, articleset=a2, is_favourite=False)
        self.assertEqual({a1, a2}, set(p1.all_articlesets()))
        self.assertTrue(isinstance(p1.all_articlesets(), QuerySet))

    def test_favourite_articlesets(self):
        """Does getting all favourite articlesets work?"""
        from django.db.models.query import QuerySet

        p1, p2 = [amcattest.create_test_project() for _x in [1,2]]
        a1 = amcattest.create_test_set(5, project=p1)
        a2 = amcattest.create_test_set(5, project=p2)

        self.assertEqual({a1}, set(p1.favourite_articlesets),
                         msg="Newly created sets should be favourites")

        # add a non-favourite
        ProjectArticleSet.objects.create(project=p1, articleset=a2, is_favourite=False)
        self.assertEqual({a1}, set(p1.favourite_articlesets),
                         msg="Non-favourite sets should not be returned")

        self.assertTrue(isinstance(p1.favourite_articlesets, QuerySet))

    def test_archived_articlesets(self):
        """Does getting all favourite articlesets work?"""
        from django.db.models.query import QuerySet

        p1, p2 = [amcattest.create_test_project() for _x in [1,2]]
        a1 = amcattest.create_test_set(5, project=p1)
        a2 = amcattest.create_test_set(5, project=p2)

        self.assertEqual(set(), set(p1.archived_articlesets),
                         msg="Newly created sets should be favourites")

        # add a non-favourite
        ProjectArticleSet.objects.create(project=p1, articleset=a2, is_favourite=False)
        self.assertEqual({a2}, set(p1.archived_articlesets),
                         msg="Favourite sets should not be returned")

        self.assertTrue(isinstance(p1.archived_articlesets, QuerySet))

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


class TestRecentProjects(amcattest.AmCATTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_update_visited(self):
        u = amcattest.create_test_user()
        p = amcattest.create_test_project(owner=u)
        dt = datetime.now()
        (rp, _) = RecentProject.update_visited(u.userprofile, p, date_visited=dt)

        qs = RecentProject.objects.filter(user=u.userprofile, project=p, date_visited=dt)
        self.assertQuerysetEqual(qs, [repr(rp)])

    def test_ordered_by_time_desc(self):
        u = amcattest.create_test_user()
        profile = u.userprofile

        p1 = amcattest.create_test_project(owner=u)
        p2 = amcattest.create_test_project(owner=u)
        p3 = amcattest.create_test_project(owner=u)

        dt1 = datetime(2015, 8, 1)
        dt2 = datetime(2015, 7, 1)
        dt3 = datetime(2015, 9, 1)

        (rp1, _) = RecentProject.update_visited(profile, p1, date_visited=dt1)
        (rp2, _) = RecentProject.update_visited(profile, p2, date_visited=dt2)
        (rp3, _) = RecentProject.update_visited(profile, p3, date_visited=dt3)

        #latest date first
        order = [rp3, rp1, rp2]
        qs = RecentProject.get_recent_projects(profile)
        self.assertQuerysetEqual(qs, map(repr, order))