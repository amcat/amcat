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
import json
from datetime import date

from django.contrib.auth.models import User

from amcat.models import ArticleSet
from amcat.scripts.query import AggregationAction
from amcat.tools import amcattest
from amcat.tools.amcates import ES


class TestQueryAction(amcattest.AmCATTestCase):
    def setUp(self):
        self.aset = amcattest.create_test_set()
        self.project = self.aset.project
        self.user = User.objects.first()
        self.asets = ArticleSet.objects.filter(id=self.aset.id)

    def _run_action(self, data, is_json=True):
        aa = AggregationAction(self.user, self.project, self.asets, data=data)

        aa_form = aa.get_form()
        aa_form.full_clean()
        self.assertTrue(aa_form.is_bound)
        self.assertTrue(aa_form.is_valid())

        if is_json:
            return json.loads(aa.run(aa_form))
        return aa.run(aa_form)

    @amcattest.use_elastic
    def test_day_aggregation(self):
        self.a1 = amcattest.create_test_article(articleset=self.aset, date=date(2011, 1, 1))
        self.a2 = amcattest.create_test_article(articleset=self.aset, date=date(2011, 1, 2))
        self.a3 = amcattest.create_test_article(articleset=self.aset, date=date(2011, 1, 2))
        ES().refresh()

        result = self._run_action({
            "output_type": "text/json+aggregation+table",
            "primary": "date_day"
        })

        self.assertEqual(result, {
                "columns": ["Value"],
                "data": [[[1]], [[2]]],
                "rows": ["2011-01-01T00:00:00", "2011-01-02T00:00:00"]
            }
        )

    @amcattest.use_elastic
    def test_week_aggregation(self):
        self.a1 = amcattest.create_test_article(articleset=self.aset, date=date(2017, 1, 1))  # week 1
        self.a2 = amcattest.create_test_article(articleset=self.aset, date=date(2017, 1, 17)) # week 4
        self.a3 = amcattest.create_test_article(articleset=self.aset, date=date(2017, 1, 17)) # week 4
        ES().refresh()

        result = self._run_action({
            "output_type": "text/json+aggregation+table",
            "fill_zeroes": True,
            "primary": "date_week"
        })

        self.assertEqual(result, {
            'columns': ['Value'],
            'rows': [
                '2016-12-26T00:00:00',
                '2017-01-02T00:00:00',
                '2017-01-09T00:00:00',
                '2017-01-16T00:00:00'
            ],
            'data': [[[1]], [[0]], [[0]], [[2]]]
        })

        result = self._run_action({
            "output_type": "text/json+aggregation+table",
            "fill_zeroes": False,
            "primary": "date_week"
        })

        self.assertEqual(result, {
            'columns': ['Value'],
            'rows': [
                '2016-12-26T00:00:00',
                '2017-01-16T00:00:00'
            ],
            'data': [[[1]], [[2]]]
        })
