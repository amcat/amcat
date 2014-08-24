from datetime import datetime
from amcat.tools import amcattest
from amcat.tools.aggregate import transpose, to_table, aggregate_by_medium, aggregate_by_term, aggregate, set_labels
from amcat.tools.amcates import ES


class TestAggregate(amcattest.AmCATTestCase):
    def set_up(self):
        # We cannot use setUp, as use_elastic deletes indices
        aset = amcattest.create_test_set()

        m1 = amcattest.create_test_medium()
        a1 = amcattest.create_test_article(text="Foo", medium=m1, articleset=aset, date=datetime(2014, 4, 3))
        a2 = amcattest.create_test_article(text="Bar", medium=m1, articleset=aset, date=datetime(2015, 4, 3))
        a3 = amcattest.create_test_article(text="FooBar", medium=amcattest.create_test_medium(), articleset=aset)

        ES().flush()
        return aset, m1, a1, a2, a3

    def test_set_labels(self):
        m1 = amcattest.create_test_medium()
        m2 = amcattest.create_test_medium()

        # Test converting x-axis
        aggregate = [(m1.id, ((2, 3),)), (m2.id, ((4, 5),))]
        self.assertEqual(
            [({"id": m1.id, "label": m1.name}, ((2, 3),)),
             ({"id": m2.id, "label": m2.name}, ((4, 5),))],
            set_labels(aggregate, [], "medium", None)
        )

        # Test converting y-axis
        aggregate = [(1, ((m1.id, 5), (m2.id, 6))), (2, ((m1.id, 9),))]
        self.assertEqual(
            [(1, (
                ({"id": m1.id, "label": m1.name}, 5),
                ({"id": m2.id, "label": m2.name}, 6))),
             (2, (({"id": m1.id, "label": m1.name}, 9),))],
            set_labels(aggregate, [], None, "medium")
        )

    @amcattest.use_elastic
    def test_aggregate(self):
        self.set_up()

        from amcat.tools.keywordsearch import SearchQuery
        query = "a# Foo* \n b# Bar"
        q1 = SearchQuery.from_string("a# Foo*")
        q2 = SearchQuery.from_string("b# Bar")

        print(aggregate(query, [q1, q2], {}, "date", "total", "day"))
        print(aggregate(query, [q1, q2], {}, "total", "date", "day"))
        print(aggregate(query, [q1, q2], {}, "date", "medium", "day"))
        print(aggregate(query, [q1, q2], {}, "medium", "date", "day"))


    @amcattest.use_elastic
    def test_aggregate_by_term(self):
        aset, _, _, _, _ = self.set_up()

        from amcat.tools.keywordsearch import SearchQuery
        q1 = SearchQuery.from_string("a# Foo*")
        q2 = SearchQuery.from_string("b# Bar")

        aggr = aggregate_by_term([q1, q2], filters={"sets": [aset.id]})
        self.assertEqual(set(aggr), {(u'a', (('#', 2),)), (u'b', (('#', 1),))})

    @amcattest.use_elastic
    def test_aggregate_by_medium(self):
        aset, m1, a1, a2, a3 = self.set_up()
        m2 = a3.medium

        self.assertEqual(
            {(m1.id, (('#', 2),)), (a3.medium_id, (('#', 1),))},
            set(aggregate_by_medium(None, filters={"sets": [aset.id]}))
        )

        self.assertEqual(
            {(m1.id, ((datetime(2014, 1, 1, 0, 0), 1),
                      (datetime(2015, 1, 1, 0, 0), 1))),
             (m2.id, ((datetime(2000, 1, 1, 0, 0), 1),))},
            set(aggregate_by_medium(None, filters={"sets": [aset.id]}, group_by="date", interval="year"))
        )

    @amcattest.use_elastic
    def test_get_table(self):
        aset, m1, a1, a2, a3 = self.set_up()
        m2 = a3.medium

        aggr = list(aggregate_by_medium(
            query=None, filters={"sets": [aset.id]},
            group_by="date", interval="year"
        ))

        self.assertEqual([
            ('', m1.id, m2.id),
            (datetime(2014, 1, 1, 0, 0), 1, 0),
            (datetime(2015, 1, 1, 0, 0), 1, 0),
            (datetime(2000, 1, 1, 0, 0), 0, 1)
        ], list(to_table(aggr)))

    def test_transpose(self):
        self.assertEqual(
            (
                (1, (('a', 5), ('b', 7),)),
                (2, (('a', 6), ('b', 4),)),
                (8, (('c', 9),          ))
            ),
            transpose((
                ("a", ((1, 5), (2, 6))),
                ("b", ((1, 7), (2, 4))),
                ("c", ((8, 9),       )),
            ))
        )
