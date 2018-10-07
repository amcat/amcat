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
import shutil
import unittest

from amcat.tools.aggregate_orm.categories import ArticleFieldCategory
from amcat.tools.table.table2spss import get_pspp_version, PSPPVersion
from django.test import TransactionTestCase

from amcat.models import Coding
from amcat.tools import amcattest, aggregate_orm
from amcat.tools.aggregate_orm import CountArticlesValue, TermCategory, ArticleSetCategory, \
    IntervalCategory
from amcat.tools.aggregate_orm import SchemafieldCategory, AverageValue
from amcat.tools.sbd import get_or_create_sentences


class TestAggregateORM(TransactionTestCase):
    fixtures = ['_initial_data.json',]

    def setUp(self):
        self.s1 = amcattest.create_test_set(5)
        self.a = list(self.s1.articles.all().order_by('id'))
        self.ids = [a.id for a in self.a]

        self.m1 = "Telegraaf"
        self.m2 = "NRC"
        self.m3 = "AD"
        self.a[0].set_property("medium", self.m1)
        self.a[1].set_property("medium", self.m2)
        self.a[2].set_property("medium", self.m2)
        self.a[3].set_property("medium", self.m3)
        self.a[4].set_property("medium", self.m3)

        self.a[0].text = "aap."
        self.a[1].text = "aap. noot."
        self.a[2].text = "aap. noot. mies."

        self.a[0].date = datetime.datetime(2015, 1, 1)
        self.a[1].date = datetime.datetime(2015, 1, 1)
        self.a[2].date = datetime.datetime(2015, 2, 1)
        self.a[3].date = datetime.datetime(2016, 1, 1)
        self.a[4].date = datetime.datetime(2016, 1, 1)
        self.a[0].save()
        self.a[1].save()
        self.a[2].save()
        self.a[3].save()
        self.a[4].save()
        
        # Uncomment if ever using elastic :)
        # self.s1.refresh_index(full_refresh=True)

        self.schema, self.codebook, self.strf, self.intf, self.codef, self.boolf, self.qualf = (
            amcattest.create_test_schema_with_fields(isarticleschema=True))

        self.sschema, self.scodebook, self.sstrf, self.sintf, self.scodef, self.sboolf, self.squalf = (
            amcattest.create_test_schema_with_fields(isarticleschema=False))

        # Article
        self.codes = self.codebook.get_codes()
        self.code_A, = [c for c in self.codes if c.label == "A"]
        self.code_B, = [c for c in self.codes if c.label == "B"]
        self.code_A1, = [c for c in self.codes if c.label == "A1"]

        # Sentence
        self.scodes = self.codebook.get_codes()
        self.scode_A, = [c for c in self.scodes if c.label == "A"]
        self.scode_B, = [c for c in self.scodes if c.label == "B"]
        self.scode_A1, = [c for c in self.scodes if c.label == "A1"]
        self.scode_A1b, = [c for c in self.scodes if c.label == "A1b"]

        # Does not get fired in unit test?
        for article in [self.a[0], self.a[1], self.a[2], self.a[3], self.a[4]]:
            get_or_create_sentences(article)

        self.job = amcattest.create_test_job(articleset=self.s1, articleschema=self.schema, unitschema=self.sschema)

        self.c1 = amcattest.create_test_coding(codingjob=self.job, article=self.a[0])
        self.c1.update_values({self.codef: self.code_A.id, self.intf: 4, self.qualf: 4})

        self.c2 = amcattest.create_test_coding(codingjob=self.job, article=self.a[1])
        self.c2.update_values({self.codef: self.code_A.id, self.intf: 2, self.qualf: 1})

        self.c3 = amcattest.create_test_coding(codingjob=self.job, article=self.a[2])
        self.c3.update_values({self.codef: self.code_B.id, self.intf: 1, self.qualf: 2})

        self.c4 = amcattest.create_test_coding(codingjob=self.job, article=self.a[3])
        self.c4.update_values({self.codef: self.code_A1.id, self.intf: 1})

        self.sentence_coding = amcattest.create_test_coding(codingjob=self.job, article=self.a[0], sentence=self.a[0].sentences.all()[0])
        self.sentence_coding.update_values({self.scodef: self.scode_A1.id, self.sintf: 1})

        self.sentence_coding = amcattest.create_test_coding(codingjob=self.job, article=self.a[2], sentence=self.a[2].sentences.all()[0])
        self.sentence_coding.update_values({self.scodef: self.scode_A1.id, self.sintf: 1})

        self.sentence_coding = amcattest.create_test_coding(codingjob=self.job, article=self.a[2], sentence=self.a[2].sentences.all()[0])
        self.sentence_coding.update_values({self.scodef: self.scode_A1b.id, self.sintf: 1})

        # Try to confuse aggregator by inserting multiple codingjobs
        job = amcattest.create_test_job(articleset=self.s1, articleschema=self.schema)
        c4 = amcattest.create_test_coding(codingjob=job, article=self.a[2])
        c4.update_values({self.codef: self.code_B.id, self.intf: 10, self.qualf: 8})

    def _get_aggr(self, **kwargs):
        article_ids = [a.id for a in self.s1.articles.all()]
        codingjob_ids = [self.job.id]
        kwargs['threaded'] = False
        return aggregate_orm.ORMAggregate.from_articles(article_ids, codingjob_ids, **kwargs)

    def test_article_field_category(self):
        aggr = self._get_aggr(flat=True)
        result = set(aggr.get_aggregate(
            [ArticleFieldCategory.from_field_name("medium")],
            [CountArticlesValue()]
        ))

        self.assertEqual(result, {
            ('Telegraaf', (1, (self.a[0].id,))),
            ('AD', (1, (self.a[3].id,))),
            ('NRC', (2, (self.a[1].id, self.a[2].id)))
        })

    def test_article_field_grouping_category(self):
        aggr = self._get_aggr(flat=True)
        result = set(aggr.get_aggregate(
            [ArticleFieldCategory.from_field_name("medium", groupings={"Telegraaf": ["AD"]})], # group AD into Telegraaf
            [CountArticlesValue()]
        ))

        self.assertEqual(result, {
            ('Telegraaf', (2, (self.a[0].id, self.a[3].id))),
            ('NRC', (2, (self.a[1].id, self.a[2].id)))
        })


    def test_one_coding(self):
        aggr = aggregate_orm.ORMAggregate(Coding.objects.filter(id__in=(self.c1.id,)), flat=True)

        result = set(aggr.get_aggregate([ArticleSetCategory()], [CountArticlesValue()]))
        self.assertEqual(result, {(self.s1, (1, (self.c1.article_id,)))})

    def test_interval_category(self):
        aggr = self._get_aggr(flat=True)
        result = set(aggr.get_aggregate([ArticleFieldCategory.from_field_name("date", interval="day")], [CountArticlesValue()]))
        self.assertEqual(result, {
            (datetime.datetime(2015, 1, 1), (2, (self.ids[0], self.ids[1]))),
            (datetime.datetime(2015, 2, 1), (1, (self.ids[2],))),
            (datetime.datetime(2016, 1, 1), (1, (self.ids[3],))),
        })

    def test_mixed_article_sentence_aggregation(self):
        """
        Aggregation should work when using an article schemafield as aggregation and
        a sentence schemafield as value.
        """
        # Aggregate on article coding, request sentence value
        aggr = self._get_aggr(flat=True)
        result = set(aggr.get_aggregate([SchemafieldCategory(self.codef, prefix="A")], [AverageValue(self.sintf, prefix="B")]))
        result = {(c, av) for (c, (av, _)) in result}
        self.assertEqual(result, {(self.scode_A, 1), (self.scode_B, 1)})

        # Aggregate on sentence coding, request article value
        aggr = self._get_aggr(flat=True)
        result = set(aggr.get_aggregate([SchemafieldCategory(self.scodef, prefix="A")], [AverageValue(self.intf, prefix="B")]))
        result = {(c, av) for (c, (av, _)) in result}
        self.assertEqual(result, {(self.code_A1, 2.5), (self.scode_A1b, 1)})


    def test_articleset_category(self):
        aggr = self._get_aggr(flat=True)
        result = set(aggr.get_aggregate([ArticleSetCategory()], [CountArticlesValue()]))
        self.assertEqual(result, {(self.s1, (4, tuple(self.ids[0:4])))})

    def test_term_category(self):
        # Test three terms
        aggr = self._get_aggr(flat=True, terms={
            "a": [self.a[0].id, self.a[1].id, self.a[2].id],
            "b": [self.a[3].id, self.a[4].id],
            "c": [self.a[0].id, self.a[3].id]
        })

        result = set(aggr.get_aggregate([TermCategory()], [CountArticlesValue()]))
        self.assertEqual(result, {
            ('a', (3, (self.a[0].id, self.a[1].id, self.a[2].id))),
            ('b', (1, (self.a[3].id,))), # Article a[4] has no coding, so won't be included!
            ('c', (2, (self.a[0].id, self.a[3].id))),
        })

        # Test empty terms
        aggr = self._get_aggr(flat=True, terms={})
        result = set(aggr.get_aggregate([TermCategory()], [CountArticlesValue()]))
        self.assertEqual(result, set())


    def test_incorrect_inputs(self):
        # You need at least one value
        self.assertRaises(ValueError, self._get_aggr().get_aggregate, categories=ArticleSetCategory())

    def test_codebook_levels(self):
        # D:
        #  +a
        #   +a1
        #   +a1b
        D = amcattest.create_test_codebook(name="D")
        D.add_code(self.scode_A)
        D.add_code(self.scode_A1, self.scode_A)
        D.add_code(self.scode_A1b, self.scode_A)

        aggr = self._get_aggr(flat=True)

        cbsf = SchemafieldCategory(self.scodef, codebook=D, level=2)
        result = set(aggr.get_aggregate([cbsf], [CountArticlesValue()]))
        self.assertEqual(result, {
            (self.scode_A1, (2, (self.ids[0], self.ids[2]))),
            (self.scode_A1b, (1, (self.ids[2],)))
        })

        # Article 3 has two sentences, one coded with A1, the other with A1b.
        # Aggregating on A must not count the article twice.
        cbsf = SchemafieldCategory(self.scodef, codebook=D)
        result = set(aggr.get_aggregate([cbsf], [CountArticlesValue()]))
        self.assertEqual(result, {(self.scode_A, (2, (1, 3)))}, msg="Articles must not be counted twice.")


    def test_codebook_avg(self):
        aggr = self._get_aggr(flat=True)

        # D: a
        #    +b
        #    +a1
        D = amcattest.create_test_codebook(name="D")
        D.add_code(self.code_A)
        D.add_code(self.code_B, self.code_A)
        D.add_code(self.code_A1, self.code_A)

        cbsf = SchemafieldCategory(self.codef, codebook=D)
        result = set(aggr.get_aggregate([cbsf], [AverageValue(self.intf)]))
        result = {(c, av) for (c, (av, _)) in result}
        self.assertEqual(result, {(self.code_A, 2.0)})

        # E: a
        #    +b
        #    a1
        E = amcattest.create_test_codebook(name="E")
        E.add_code(self.code_A)
        E.add_code(self.code_B, self.code_A)
        E.add_code(self.code_A1)

        cbsf = SchemafieldCategory(self.codef, codebook=E)
        result = set(aggr.get_aggregate([cbsf], [AverageValue(self.intf)]))
        result = {(c, av) for (c, (av, _)) in result}
        self.assertEqual(result, {
            (self.code_A1, 1.0),
            (self.code_A, 7.0/3.0),
        })

    def test_avg_per_code(self):
        """Tests aggregate ORM with single aggregation and single value"""
        aggr = self._get_aggr(flat=True)

        result = set(aggr.get_aggregate([SchemafieldCategory(self.codef)], [AverageValue(self.intf)]))
        result = {(c, av) for (c, (av, _)) in result}
        self.assertEqual(result, {(self.code_A, 3.0), (self.code_B, 1.0), (self.code_A1, 1.0)})

    def test_quality_field(self):
        aggr = self._get_aggr(flat=True)
        result = set(aggr.get_aggregate([SchemafieldCategory(self.codef)], [AverageValue(self.qualf)]))
        result = {(c, av) for (c, (av, _)) in result}
        self.assertEqual(result, {(self.code_A, 0.25), (self.code_B, 0.2)})

    def test_secondary_axis(self):
        """Test whether we can do count plus average per something"""
        aggr = self._get_aggr(flat=True)

        result = (set(aggr.get_aggregate(
            categories=[SchemafieldCategory(self.codef)],
            values=[CountArticlesValue(), AverageValue(self.intf)]
        )))
        result = {(c, (a[0], b[0])) for (c, (a, b)) in result}

        self.assertEqual(result, {(self.code_A, (2, 3.0)), (self.code_B, (1, 1.0)), (self.code_A1, (1, 1.0))})

    def test_medium_per_code(self):
        """Test whether we can use code field as secondary aggregation"""
        aggr = self._get_aggr(flat=True)

        # Two categories + count
        result = set(aggr.get_aggregate(
            categories=[ArticleFieldCategory.from_field_name("medium"), SchemafieldCategory(self.codef)],
            values=[CountArticlesValue()]
        ))
        result = {(c, av) for (c, (av, _)) in result}
        
        self.assertEqual(result, {
            ((self.m1, self.code_A), 1),
            ((self.m2, self.code_A), 1),
            ((self.m2, self.code_B), 1),
            ((self.m3, self.code_A1), 1)
        })

        # Two categories + average
        result = set(aggr.get_aggregate(
            categories=[ArticleFieldCategory.from_field_name("medium"), SchemafieldCategory(self.codef)],
            values=[AverageValue(self.intf)]
        ))
        result = {(c, av) for (c, (av, _)) in result}

        self.assertEqual(result, {
            ((self.m1, self.code_A), 4.0),
            ((self.m2, self.code_A), 2.0),
            ((self.m2, self.code_B), 1.0),
            ((self.m3, self.code_A1), 1.0)
        })

        # Two categories + 2 values
        result = set(aggr.get_aggregate(
            categories=[ArticleFieldCategory.from_field_name("medium"), SchemafieldCategory(self.codef)],
            values=[AverageValue(self.intf), CountArticlesValue()]
        ))
        result = {(c, (x, y)) for (c, ((x, xs), (y, ys))) in result}

        self.assertEqual(result, {
            ((self.m1, self.code_A), (4.0, 1)),
            ((self.m2, self.code_A), (2.0, 1)),
            ((self.m2, self.code_B), (1.0, 1)),
            ((self.m3, self.code_A1), (1.0, 1))
        })

    def test_empty(self):
        aggr = self._get_aggr(flat=True)

        # We allow empty values (default)
        result = set(aggr.get_aggregate(
            categories=[SchemafieldCategory(self.codef)],
            values=[AverageValue(self.intf), AverageValue(self.qualf)]
        ))

        result = {(c, (ra[0], rb[0] if rb is not None else None))
                  for (c, (ra, rb)) in result}

        self.assertEqual(result, {
            (self.code_A, (3.0, 0.25)),
            (self.code_B, (1.0, 0.2)),
            (self.code_A1, (1.0, None)),
        })

        # Do not allow empty values
        result = set(aggr.get_aggregate(
            categories=[SchemafieldCategory(self.codef)],
            values=[AverageValue(self.intf), AverageValue(self.qualf)],
            allow_empty=False
        ))

        result = {(c, (ra[0], rb[0] if rb is not None else None))
                  for (c, (ra, rb)) in result}

        self.assertEqual(result, {
            (self.code_A, (3.0, 0.25)),
            (self.code_B, (1.0, 0.2))
        })

    def test_count(self):
        """Tests whether count values work"""
        aggr = self._get_aggr(flat=True)
        result = set(aggr.get_aggregate([SchemafieldCategory(self.codef)], [CountArticlesValue()]))
        result = {(c, ct) for (c, (ct, _)) in result}
        self.assertEqual(result, {(self.code_A, 2), (self.code_B, 1), (self.code_A1, 1)})

    def test_no_codings(self):
        aggr = aggregate_orm.ORMAggregate(Coding.objects.none(), threaded=False)
        self.assertEqual(set(aggr.get_aggregate(values=[CountArticlesValue()])), set())

    @unittest.skipUnless(shutil.which("pspp"), "PSPP not installed")
    def test_get_pspp_version(self):
        self.assertGreaterEqual(PSPPVersion(8, 5, 0), get_pspp_version())
