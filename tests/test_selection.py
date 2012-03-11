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

DEFAULTS = dict(datetype="all", columns=['article_id'])

class TestArticleList(amcattest.PolicyTestCase):

    def _run(self, **kargs):
        options = DEFAULTS.copy()
        options.update(kargs)
        return ArticleListScript(**options).run()
    
    def test_selection(self):
        """Can we select articles outside the project?"""
        
        p = amcattest.create_test_project()
        arts = {amcattest.create_test_article(project=p) for i in range(10)}

        
        articles = self._run(projects=[p.id])
        self.assertEqual(set(articles), arts)
        
        p2 = amcattest.create_test_project()
        s = amcattest.create_test_set(project=p2)
        s.articles.add(*arts)

        articles = self._run(projects=[p2.id])
        self.assertEqual(len(articles), 0)

        
        articles = self._run(projects=[p2.id], articlesets=[s.id])
        self.assertEqual(set(articles), arts)

        

        
