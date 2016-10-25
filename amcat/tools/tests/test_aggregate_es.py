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

from amcat.models import ArticleSet
from amcat.tools import amcattest
from amcat.tools.aggregate_es.aggregate import aggregate
from amcat.tools.aggregate_es.categories import ArticlesetCategory, IntervalCategory, \
    TermCategory, FieldCategory
from amcat.tools.amcates import ES
from amcat.tools.keywordsearch import SearchQuery


class TestAggregateES(amcattest.AmCATTestCase):
    def set_up(self):
        self.a1 = amcattest.create_test_article()
        self.a1.text = "aap noot mies"
        self.a1.date = datetime.datetime(2010, 1, 1)
        self.a1.properties = {"author": "De Bas", "length_int": 5}
        self.a1.save()

        self.a2 = amcattest.create_test_article()
        self.a2.text = "aap noot geit"
        self.a2.date = datetime.datetime(2010, 1, 1)
        self.a2.properties = {"author": "Het Martijn", "length_int": 5}
        self.a2.save()

        self.a3 = amcattest.create_test_article()
        self.a3.text = "lamp"
        self.a3.date = datetime.datetime(2010, 1, 2)
        self.a3.properties = {"author": "Het Martijn", "length_int": 15}
        self.a3.save()

        self.aset1 = amcattest.create_test_set()
        self.aset1.add_articles([self.a1, self.a2])
        self.aset1.refresh_index(True)

        self.aset2 = amcattest.create_test_set()
        self.aset2.add_articles([self.a3])
        self.aset2.refresh_index(True)

        ES().flush()

    def aggregate(self, **kwargs):
        aggr_args = {"filters": {"sets": list(ArticleSet.objects.all().values_list("id", flat=True))}}
        aggr_args.update(**kwargs)
        return set(aggregate(**aggr_args))

    @amcattest.use_elastic
    def test_field_category(self):
        self.set_up()

        all_articlesets = ArticleSet.objects.filter(id__in=(self.aset1.id, self.aset2.id))

        self.assertEqual(
            self.aggregate(categories=[ArticlesetCategory(all_articlesets)]),
            {(self.aset1, 2), (self.aset2, 1)}
        )

        self.assertEqual(
            self.aggregate(categories=[FieldCategory.from_fieldname("author")]),
            {("Het Martijn", 2), ("De Bas", 1)}
        )

        self.assertEqual(
            self.aggregate(categories=[FieldCategory.from_fieldname("length_int")]),
            {(5, 2),(15, 1)}
        )

        self.assertEqual(
            self.aggregate(categories=[FieldCategory.from_fieldname("author"), FieldCategory.from_fieldname("length_int")]),
            {('De Bas', 5, 1), ('Het Martijn', 5, 1), ('Het Martijn', 15, 1)}
        )

        self.assertRaises(ValueError, lambda: FieldCategory.from_fieldname("date"))
        self.assertRaises(ValueError, lambda: FieldCategory("abc"))



    @amcattest.use_elastic
    def test_articleset_category(self):
        self.set_up()

        # Do not limit articlesets
        result = self.aggregate(categories=[ArticlesetCategory()])
        self.assertEqual(result, {
            (self.aset1, 2),
            (self.aset2, 1)
        })

        # Limit articlesets
        category = ArticlesetCategory(ArticleSet.objects.filter(id__in=[self.aset1.id]))
        result = self.aggregate(categories=[category])
        self.assertEqual(result, {
            (self.aset1, 2)
        })

    @amcattest.use_elastic
    def test_interval_category(self):
        self.set_up()

        result = self.aggregate(categories=[IntervalCategory("day")])
        self.assertEqual(result, {
            (datetime.datetime(2010, 1, 2, 0, 0), 1),
            (datetime.datetime(2010, 1, 1, 0, 0), 2),
        })

    @amcattest.use_elastic
    def test_term_category(self):
        self.set_up()

        term1 = SearchQuery("aap")
        term2 = SearchQuery("noot")
        term3 = SearchQuery("lamp")


        result = self.aggregate(categories=[TermCategory([term1, term2, term3])])
        self.assertEqual(result, {
            (term1, 2),
            (term2, 2),
            (term3, 1)
        })

    @amcattest.use_elastic
    def test_multiple_categories(self):
        self.set_up()

        term1 = SearchQuery("aap")
        term2 = SearchQuery("noot")
        term3 = SearchQuery("lamp")

        cat1 = TermCategory([term1, term2, term3])
        cat2 = IntervalCategory("day")

        result = self.aggregate(categories=[cat1, cat2])
        self.assertEqual(result, {
            (term1, datetime.datetime(2010, 1, 1, 0, 0), 2),
            (term2, datetime.datetime(2010, 1, 1, 0, 0), 2),
            (term3, datetime.datetime(2010, 1, 2, 0, 0), 1)
        })

    @amcattest.use_elastic
    def test_no_objects(self):
        self.set_up()

        term1 = SearchQuery("aap")
        term2 = SearchQuery("noot")

        result = self.aggregate(categories=[TermCategory([term1, term2])], objects=False)
        self.assertEqual(result, {
            ("aap", 2),
            ("noot", 2)
        })
