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

from amcat.models import Article, ArticleSet
from amcat.tools import amcates
from amcat.tools import amcattest
from amcat.tools.amcates_queryset import ESQuerySet, merge_highlighted

now = datetime.datetime.now()


class TestAmcatesQuerySet(amcattest.AmCATTestCase):
    def set_up(self):
        self.aset = amcattest.create_test_set()
        self.asets = ArticleSet.objects.filter(id__in=[self.aset.id])
        self.project = self.aset.project

        self.a1 = Article(
            title="Man leeft nog steeds in de gloria",
            text="Gezongen vloek op verjaardag maakt leven van man tot een vrolijke hel.",
            date=datetime.datetime(2017, 1, 2, 23, 22, 11),
            author="Rudolf Julius",
            publisher="De Speld",
            project=self.project,
            exists="Once",
            page_int=5,
            section_int=10
        )

        self.a2 = Article(
            title="VVD trots op opkomende zon",
            text="Kabinetsbeleid om geen parasol over Nederland te zetten betaalt zich uit",
            date=datetime.datetime(2016, 12, 14, 15, 13, 12),
            author="Thomas Hogeling",
            publisher="De Speld",
            project=self.project,
            page_int=5,
            section_int=11
        )

        Article.create_articles([self.a1, self.a2], articleset=self.aset)

        amcates.ES().refresh()

        self.qs = ESQuerySet(self.asets)

    @amcattest.use_elastic
    def test_exact_filter(self):
        self.set_up()

        # TODO:
        #print(list(self.qs.filter(author__exact="Thomas Hogeling")))
        #print(list(self.qs.filter(author__exact__in=["Thomas Hogeling"])))


    @amcattest.use_elastic
    def test_order_by_random(self):
        self.set_up()

        # Deterministic run, all values should be the same (P < 1e-6):
        ids = []
        for i in range(20):
            ids.append(tuple(self.qs.order_by("?", seed=0).values_list("id", flat=True)))
        self.assertTrue(all(ids[0] == id for id in ids))

        # Random run, query should be different sometimes
        ids = []
        for i in range(20):
            ids.append(tuple(self.qs.order_by("?").values_list("id", flat=True)))
        self.assertFalse(all(ids[0] == id for id in ids))

    @amcattest.use_elastic
    def test_order_by(self):
        self.set_up()

        self.assertEqual(
            list(self.qs.order_by("date").values_list("id", flat=True)),
            [self.a2.id, self.a1.id]
        )

        self.assertEqual(
            list(self.qs.order_by("-date").values_list("id", flat=True)),
            [self.a1.id, self.a2.id]
        )

        self.assertEqual(
            list(self.qs.order_by("page_int", "section_int").values_list("id", flat=True)),
            [self.a1.id, self.a2.id]
        )

        self.assertEqual(
            list(self.qs.order_by("page_int", "-section_int").values_list("id", flat=True)),
            [self.a2.id, self.a1.id]
        )


    @amcattest.use_elastic
    def test_simple(self):
        self.set_up()

        qs = ESQuerySet(self.asets)
        self.assertEqual(
            {art.id for art in qs},
            {self.a1.id, self.a2.id}
        )

    @amcattest.use_elastic
    def test_only(self):
        self.set_up()
        self.assertEqual({"date"}, set(next(iter(self.qs.only("date"))).to_dict().keys()))
        self.assertEqual({"date", "author"}, set(next(iter(self.qs.only("date", "author"))).to_dict().keys()))
        self.assertRaises(ValueError, self.qs.only, "non-existent")

    @amcattest.use_elastic
    def test_filter(self):
        self.set_up()
        self.assertEqual(2, len(self.qs))
        self.assertEqual(2, len(self.qs.filter(date__lte="2018-1-1")))
        self.assertEqual(1, len(self.qs.filter(date__lte="2017-1-1")))
        self.assertEqual(0, len(self.qs.filter(date__lte="2016-1-1")))
        self.assertEqual(1, len(self.qs.filter(date__on="2017-1-2")))
        self.assertEqual(0, len(self.qs.filter(date__on="2017-1-1")))
        self.assertEqual(1, len(self.qs.filter(date__on="2017-1-2T23:22:11")))
        self.assertEqual(1, len(self.qs.filter(id=self.a1.id)))
        self.assertEqual(2, len(self.qs.filter(id__in=[self.a1.id, self.a2.id])))
        self.assertEqual(2, len(self.qs.filter(id__in=[self.a1.id, self.a2.id, -1])))

    @amcattest.use_elastic
    def test_query(self):
        self.set_up()
        self.assertEqual(2, len(self.qs.query("op")))
        self.assertEqual(1, len(self.qs.query("zon")))
        self.assertEqual(1, len(self.qs.query("vloek")))
        self.assertEqual(0, len(self.qs.query("title:vloek")))
        self.assertEqual(1, len(self.qs.query("text:vloek")))

    @amcattest.use_elastic
    def test_values_list(self):
        self.set_up()

        self.assertEqual(
            set(self.qs.values_list("date", flat=True)),
            {self.a1.date, self.a2.date}
        )

        self.assertRaises(ValueError, self.qs.values_list, flat=True)
        self.assertRaises(ValueError, self.qs.values_list, "id", "date", flat=True)

        self.assertEqual(
            set(self.qs.values_list("date", flat=True)),
            {self.a1.date, self.a2.date}
        )

        self.assertEqual(
            set(self.qs.values_list("date")),
            {(self.a1.date,), (self.a2.date,)}
        )

        self.assertEqual(
            set(self.qs.values_list("id", "date")),
            {(self.a1.id, self.a1.date,), (self.a2.id, self.a2.date,)}
        )

        self.assertEqual(
            set(self.qs.values_list("id", "exists")),
            {(self.a1.id, "Once"), (self.a2.id, None)}
        )

    @amcattest.use_elastic
    def test_highlight(self):
        self.set_up()

        # Test one field
        highlighted = self.qs.only("title", "text").highlight("opkomende", ("title",), add_filter=True)
        self.assertEqual(1, len(highlighted))
        self.assertEqual("VVD trots op <mark0>opkomende</mark0> zon", highlighted[0].title)

        # Multiple fields
        highlighted = self.qs.only("title", "text").highlight("man", ("title",), add_filter=True)
        self.assertEqual(1, len(highlighted))
        self.assertEqual("<mark0>Man</mark0> leeft nog steeds in de gloria", highlighted[0].title)
        self.assertEqual("Gezongen vloek op verjaardag maakt leven van man tot een vrolijke hel.", highlighted[0].text)

        highlighted = self.qs.only("title", "text").highlight("man", ("title", "text"), add_filter=True)
        self.assertEqual(1, len(highlighted))
        self.assertEqual("<mark0>Man</mark0> leeft nog steeds in de gloria", highlighted[0].title)
        self.assertEqual("Gezongen vloek op verjaardag maakt leven van <mark0>man</mark0> tot een vrolijke hel.", highlighted[0].text)

        # Highlighter should force fetching of fields if specified in highlight, but not in fields
        highlighted = self.qs.only("date").highlight("man", ("title", "text"), add_filter=True)
        self.assertEqual(1, len(highlighted))
        self.assertEqual({"date", "title", "text"}, set(highlighted[0]._fields))

        # We should be able to access not highlighted fields
        highlighted = self.qs.only("title", "text").highlight("man", ("title", "text"), add_filter=True)
        self.assertEqual(1, len(highlighted))
        non_highlighted = highlighted[0].get_non_highlighted()
        self.assertEqual("Man leeft nog steeds in de gloria", non_highlighted.title)
        self.assertEqual("Gezongen vloek op verjaardag maakt leven van man tot een vrolijke hel.", non_highlighted.text)

    @amcattest.use_elastic
    def test_highlight_multiple(self):
        self.set_up()

        # Test non-overlapping
        filtered = self.qs.only("title").filter_query("man")
        highlighted = filtered.highlight("man", ("title",)).highlight("gloria", ("title",))
        self.assertEqual(next(iter(highlighted)).title, "<mark0>Man</mark0> leeft nog steeds in de <mark1>gloria</mark1>")

        # Test overlapping
        filtered = self.qs.only("title").filter_query("man")
        highlighted = filtered.highlight("man", ("title",)).highlight('"man leeft"', ("title",))
        self.assertEqual(next(iter(highlighted)).title, "<mark1><mark0>Man</mark0></mark1> <mark1>leeft</mark1> nog steeds in de gloria")

    @amcattest.use_elastic
    def test_highlight_complex(self):
        self.set_up()

        # Test match_phrase
        query = '"op opkomende"'
        highlighted = self.qs.only("title").filter_query(query).highlight(query, ("title",))
        self.assertEqual(
            list(highlighted)[0].title,
            "VVD trots <mark0>op</mark0> <mark0>opkomende</mark0> zon"
        )

        # Test OR
        query = '"op opkomende" OR vvd'
        highlighted = self.qs.only("title").filter_query(query).highlight(query, ("title",))
        self.assertEqual(
            list(highlighted)[0].title,
            "<mark0>VVD</mark0> trots <mark0>op</mark0> <mark0>opkomende</mark0> zon"
        )

    def test_merge_highlighted_texts(self):
        text = "Gezongen  vloek op verjaardag maakt leven van man tot een vrolijke hel."
        text1 = "Gezongen  vloek op verjaardag maakt leven van man tot een <mark1>vrolijke</mark1> hel."
        text2 = "Gezongen  vloek op verjaardag maakt leven van <mark2>man</mark2> tot een <mark2>vrolijke</mark2> hel."
        merged = "".join(merge_highlighted(text, [text1, text2], ["mark1", "mark2"]))
        self.assertEqual(merged, "Gezongen  vloek op verjaardag maakt leven van <mark2>man</mark2> tot een <mark2><mark1>vrolijke</mark1></mark2> hel.")

        text = "  Gezongen  vloek op verjaardag maakt leven van man tot een vrolijke hel."
        text1 = "  Gezongen  vloek op verjaardag maakt leven van man tot een <mark1>vrolijke</mark1> hel."
        text2 = "  Gezongen  vloek op verjaardag maakt leven van <mark2>man</mark2> tot een <mark2>vrolijke</mark2> hel."
        merged = "".join(merge_highlighted(text, [text1, text2], ["mark1", "mark2"]))
        self.assertEqual(merged, "  Gezongen  vloek op verjaardag maakt leven van <mark2>man</mark2> tot een <mark2><mark1>vrolijke</mark1></mark2> hel.")

        text = "Gezongen  vloek op verjaardag maakt leven van man tot een vrolijke hel.  "
        text1 = "Gezongen  vloek op verjaardag maakt leven van man tot een <mark1>vrolijke</mark1> hel.  "
        text2 = "Gezongen  vloek op verjaardag maakt leven van <mark2>man</mark2> tot een <mark2>vrolijke</mark2> hel.  "
        merged = "".join(merge_highlighted(text, [text1, text2], ["mark1", "mark2"]))
        self.assertEqual(merged, "Gezongen  vloek op verjaardag maakt leven van <mark2>man</mark2> tot een <mark2><mark1>vrolijke</mark1></mark2> hel.  ")

        text = "  Gezongen  vloek op verjaardag maakt leven van man tot een vrolijke hel.  "
        text1 = "  Gezongen  vloek op verjaardag maakt leven van man tot een <mark1>vrolijke</mark1> hel.  "
        text2 = "  Gezongen  vloek op verjaardag maakt leven van <mark2>man</mark2> tot een <mark2>vrolijke</mark2> hel.  "
        merged = "".join(merge_highlighted(text, [text1, text2], ["mark1", "mark2"]))
        self.assertEqual(merged, "  Gezongen  vloek op verjaardag maakt leven van <mark2>man</mark2> tot een <mark2><mark1>vrolijke</mark1></mark2> hel.  ")

