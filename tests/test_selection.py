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
Testing module for the article selection scripts
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools import amcattest

from amcat.scripts.searchscripts.articlelist import ArticleListScript
from amcat.scripts.searchscripts.aggregation import AggregationScript, AggregationForm

from django.utils.datastructures import MultiValueDict

        
DEFAULTS = dict(datetype="all", columns=['article_id'], yAxis='total', counterType='numberOfArticles')

class TestArticleList(amcattest.PolicyTestCase):

    def list(self, **kargs):
        options = DEFAULTS.copy()
        options.update(kargs)
        return set(ArticleListScript(**options).run())

    def aggr(self, **kargs):
        options = DEFAULTS.copy()
        options.update(kargs)
        return list(AggregationScript(**options).run().to_list(tuple_name=None))
    
    def test_selection(self):
        """Can we select articles outside the project?"""

        # baseline: can we select articles in a project
        p = amcattest.create_test_project()
        arts = {amcattest.create_test_article(project=p) for i in range(10)}
        
        self.assertEqual(self.list(projects=[p.id]), arts)

        # add second project with articles from first project in set
        p2 = amcattest.create_test_project()
        s = amcattest.create_test_set(project=p2)
        s.articles.add(*arts)
        # selecting on only project should give {}, but on set should give articles
        self.assertEqual(self.list(projects=[p2.id]), set())
        self.assertEqual(self.list(projects=[p2.id], articlesets=[s.id]), arts)

    def test_aggregation(self):
        """Can we create nice tables?"""
        p = amcattest.create_test_project()
        m1, m2 = [amcattest.create_test_medium() for x in [1,2]]
        arts1 = {amcattest.create_test_article(project=p, medium=m1) for i in range(5)}
        arts2 = {amcattest.create_test_article(project=p, medium=m2) for i in range(15)}

        # can we select on mediumid
        self.assertEqual(self.list(projects=[p.id]), arts1|arts2)
        self.assertEqual(self.list(projects=[p.id], mediums=[m1.id]), arts1)

        # can we make a table?
        x = self.aggr(projects=[p.id], xAxis='medium')
        self.assertEqual(set(x), {(5,), (15,)})

        
        # add second project with articles from first project in set
        p2 = amcattest.create_test_project()
        s = amcattest.create_test_set(project=p2)
        s.articles.add(*(arts1|arts2))
        x = self.aggr(projects=[p2.id], articlesets=[s.id], xAxis='medium')

    def test_form(self):
        p = amcattest.create_test_project()
        arts = {amcattest.create_test_article(project=p) for i in range(10)}
        form = dict(yAxis=['medium'], counterType=['numberOfArticles'], articlesets=[],
                    xAxis=[u'date'], datetype=['all'], projects=[unicode(p.id)])
        
        #f = AggregationForm(data=MultiValueDict(form))
        #valid = f.is_valid()
        #self.assertTrue(valid, "Validation errors: {f.errors}".format(**locals()))

        s = amcattest.create_test_set(project=p)
        form['articlesets'] = [unicode(s.id)]
        f = AggregationForm(data=MultiValueDict(form))
        valid = f.is_valid()
        self.assertTrue(valid, "Validation errors: {f.errors}".format(**locals()))
        
