##########################################################################
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

from amcat.scripts.query import ArticleListAction
from amcat.tools import amcattest
from django.http import QueryDict


class TestArticleListAction(amcattest.AmCATTestCase):
    def setUp(self):
        self.project = amcattest.create_test_project()
        self.articleset = amcattest.create_test_set(4, project=self.project)

    def get_query_action(self, query="text/html"):
        return ArticleListAction(
            user=self.project.owner, project=self.project,
            articlesets=self.project.all_articlesets(),
            data=QueryDict(query)
        )

    def test_basic(self):
        action = self.get_query_action("output_type=text/html")
        form = action.get_form()
        form.full_clean()
        str(action.run(form))
