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
import datetime

from django.db.models import F, Avg

from amcat.tools import amcattest, aggregate_orm
from amcat.tools.aggregate_orm import MediumCategory, Count
from amcat.tools.aggregate_orm import SchemafieldCategory, Average


class TestAggregateORM(amcattest.AmCATTestCase):
    def setUp(self):
        self.s1 = amcattest.create_test_set(4)
        self.a1, self.a2, self.a3, self.a4 = self.s1.articles.all()
        self.m1 = self.a1.medium
        self.m2 = self.a2.medium
        self.a3.medium = self.m2
        self.a3.save()

        self.a1.date = datetime.datetime(2015, 01, 01)
        self.a2.date = datetime.datetime(2015, 01, 01)
        self.a3.date = datetime.datetime(2015, 02, 01)
        self.a4.date = datetime.datetime(2016, 01, 01)
        self.a1.save()
        self.a2.save()
        self.a3.save()
        self.a4.save()

        # Uncomment if ever using elastic :)
        # self.s1.refresh_index(full_refresh=True)

        self.schema, self.codebook, self.strf, self.intf, self.codef, self.boolf, self.qualf = (
            amcattest.create_test_schema_with_fields(isarticleschema=True))

        self.codes = self.codebook.get_codes()
        self.code_A, = [c for c in self.codes if c.label == "A"]
        self.code_B, = [c for c in self.codes if c.label == "B"]

        self.job = amcattest.create_test_job(articleset=self.s1, articleschema=self.schema)

        self.c1 = amcattest.create_test_coding(codingjob=self.job, article=self.a1)
        self.c1.update_values({self.codef: self.code_A.id, self.intf: 4, self.qualf: 4})

        self.c2 = amcattest.create_test_coding(codingjob=self.job, article=self.a2)
        self.c2.update_values({self.codef: self.code_A.id, self.intf: 2, self.qualf: 1})

        self.c3 = amcattest.create_test_coding(codingjob=self.job, article=self.a3)
        self.c3.update_values({self.codef: self.code_B.id, self.intf: 1, self.qualf: 2})

        # Try to confuse aggregator by inserting multiple codingjobs
        job = amcattest.create_test_job(articleset=self.s1, articleschema=self.schema)
        c4 = amcattest.create_test_coding(codingjob=job, article=self.a3)
        c4.update_values({self.codef: self.code_B.id, self.intf: 10, self.qualf: 8})

    def _get_aggr(self, flat=False):
        article_ids = [a.id for a in self.s1.articles.all()]
        codingjob_ids = [self.job.id]
        return aggregate_orm.ORMAggregate.from_articles(article_ids, codingjob_ids, flat=flat)

    def test_incorrect_inputs(self):
        # You need at least one value
        self.assertRaises(ValueError, self._get_aggr().get_aggregate, categories=MediumCategory())

    def test_avg_per_code(self):
        """Tests aggregate ORM with single aggregation and single value"""
        aggr = self._get_aggr(flat=True)

        result = set(aggr.get_aggregate([SchemafieldCategory(self.codef)], [Average(self.intf)]))
        self.assertEqual(result, {(self.code_A, 3.0), (self.code_B, 1.0)})

        result = set(aggr.get_aggregate([MediumCategory()], [Average(self.intf)]))
        self.assertEqual(result, {(self.m1, 4.0), (self.m2, 1.5)})

    def test_quality_field(self):
        aggr = self._get_aggr(flat=True)
        result = set(aggr.get_aggregate([SchemafieldCategory(self.codef)], [Average(self.qualf)]))
        self.assertEqual(result, {(self.code_A, 0.25), (self.code_B, 0.2)})

    def test_secondary_axis(self):
        """Test whether we can do count plus average per something"""
        aggr = self._get_aggr(flat=True)

        result = (set(aggr.get_aggregate(
            categories=[SchemafieldCategory(self.codef)],
            values=[Count(), Average(self.intf)]
        )))

        self.assertEqual(result, {(self.code_A, (2, 3.0)), (self.code_B, (1, 1.0))})


    def test_medium_per_code(self):
        """Test whether we can use code field as secondary aggregation"""
        aggr = self._get_aggr(flat=True)

        # Two categories + count
        result = set(aggr.get_aggregate(
            categories=[MediumCategory(), SchemafieldCategory(self.codef)],
            values=[Count()]
        ))
        
        self.assertEqual(result, {
            ((self.m1, self.code_A), 1),
            ((self.m2, self.code_A), 1),
            ((self.m2, self.code_B), 1)
        })

        # Two categories + average
        result = set(aggr.get_aggregate(
            categories=[MediumCategory(), SchemafieldCategory(self.codef)],
            values=[Average(self.intf)]
        ))

        self.assertEqual(result, {
            ((self.m1, self.code_A), 4.0),
            ((self.m2, self.code_A), 2.0),
            ((self.m2, self.code_B), 1.0)
        })

        # Two categories + 2 values
        result = set(aggr.get_aggregate(
            categories=[MediumCategory(), SchemafieldCategory(self.codef)],
            values=[Average(self.intf), Count()]
        ))

        self.assertEqual(result, {
            ((self.m1, self.code_A), (4.0, 1)),
            ((self.m2, self.code_A), (2.0, 1)),
            ((self.m2, self.code_B), (1.0, 1))
        })

        
    def test_count(self):
        """Tests whether count values work"""
        aggr = self._get_aggr(flat=True)
        result = set(aggr.get_aggregate([SchemafieldCategory(self.codef)], [Count()]))
        self.assertEqual(result, {(self.code_A, 2), (self.code_B, 1)})
