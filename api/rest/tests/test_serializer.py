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
from amcat.tools.amcates import ES
from amcat.tools.toolkit import read_date
from api.rest.apitestcase import ApiTestCase
from api.rest.resources import ArticleMetaResource, ProjectResource


class TestSerializer(ApiTestCase):
    @amcattest.use_elastic
    def test_get_object(self):
        a = amcattest.create_test_article(
            title=u'\xba\xa2\u0920\u0903\u0905\u0920\u0940\u1e00\u1e80\u1eb6\u1ef3')
        # (why not test some unicode while we're at it...)
        ES().refresh()
        a2 = self.get_object(ArticleMetaResource, a.id)
        self.assertEqual(a.title, a2.title)
        self.assertEqual(a.id, a2.id)

    def test_echo(self):
        res = self.get(ProjectResource, datatables_options='{"sEcho":5}')
        self.assertEqual(res['echo'], 5)

    def test_get(self):
        p1 = amcattest.create_test_project(name="testnaam", description="testdescription",
                                           insert_date='2012-01-01')

        actual = self.get(ProjectResource, id=p1.id)

        actual_results = actual.pop("results")
        self.assertEqual(len(actual_results), 1)
        actual_results = actual_results[0]

        date = actual_results.pop('insert_date')
        read_date(date)  # check valid date, not much more to check here?

        expected_results = {
            'insert_user': p1.insert_user.id,
            'description': 'testdescription',
            'name': u'testnaam',
            'guest_role': 11,
            'owner': p1.owner.id,
            'active': True,
            'id': p1.id,
            'last_visited_at': "Never",
            'favourite': False,
            "r_plugins_enabled": False
        }

        expected_meta = {
            'page': 1,
            'next': None,
            'previous': None,
            'per_page': 10,
            'total': 1,
            'pages': 1,
            'echo': None,
        }

        self.assertDictsEqual(actual, expected_meta)
        self.assertDictsEqual(actual_results, expected_results)
