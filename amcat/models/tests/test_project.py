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

from amcat.tools import amcattest
from django.db.models.query import QuerySet


class TestProject(amcattest.AmCATTestCase):
    def test_create(self):
        """Can we create a project and access its attributes?"""
        p = amcattest.create_test_project(name="Test")
        self.assertEqual(p.name, "Test")

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