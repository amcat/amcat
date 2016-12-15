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

import iso8601
from django.conf import settings
from amcat.models import Article
from amcat.tools import amcattest
from amcat.tools.amcates import ES, get_article_dict, ALL_FIELDS, get_property_primitive_type
from amcat.tools.amcattest import create_test_project
from amcat.tools.keywordsearch import SearchQuery

class TestAmcatES(amcattest.AmCATTestCase):
    def setup(self):
        s1 = amcattest.create_test_set()
        s2 = amcattest.create_test_set()
        a = amcattest.create_test_article(text='aap noot mies', title='m1', date='2001-01-01', create=False)
        b = amcattest.create_test_article(text='noot mies wim zus', title='m2', date='2001-02-01', create=False)
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', title='m2', date='2002-01-01', create=False)
        d = amcattest.create_test_article(text='noot mies wim zus', title='m2', date='2001-02-03', create=False)
        e = amcattest.create_test_article(text='aap noot mies', title='m3', articleset=s2)

        Article.create_articles([a, b, c, d], articleset=s1)
        ES().flush()
        return s1, s2, a, b, c, d, e

    def test_get_property_primitive_type(self):
        # Special property names
        self.assertEqual(get_property_primitive_type("sets"), int)
        self.assertEqual(get_property_primitive_type("text"), str)
        self.assertEqual(get_property_primitive_type("hash"), str)
        self.assertEqual(get_property_primitive_type("date"), datetime.datetime)
        self.assertEqual(get_property_primitive_type("url"), str)
        self.assertEqual(get_property_primitive_type("title"), str)
        self.assertEqual(get_property_primitive_type("hash"), str)
        self.assertEqual(get_property_primitive_type("id"), int)

        # User-defined properties
        self.assertEqual(get_property_primitive_type("foo_date"), datetime.datetime)
        self.assertEqual(get_property_primitive_type("foo_num"), float)
        self.assertEqual(get_property_primitive_type("foo_int"), int)
        self.assertEqual(get_property_primitive_type("foo_url"), str)
        self.assertEqual(get_property_primitive_type("foo_id"), str)

    @amcattest.use_elastic
    def test_purge_orphans(self):
        s1, s2, a, b, c, d, e = self.setup()

        # Query without deleting
        all_ids = {a.id, b.id, c.id, d.id, e.id}
        ES().flush()
        self.assertEqual(all_ids, set(ES().query_ids()))

        # Delete but do not purge orphans, query again
        missing_query =  {"query": {"constant_score": {"filter": {"missing": {"field": "sets"}}}}}
        s1.delete(purge_orphans=False)
        ES().flush()
        self.assertEqual(all_ids, set(ES().query_ids()))
        self.assertEqual(all_ids - {e.id}, set(ES().query_ids(body=missing_query)))

        # Purge orphans, query again
        ES().purge_orphans()
        ES().flush()

    @amcattest.use_elastic
    def test_aggregate(self):
        """Can we make tables per date interval?"""
        s1, s2, a, b, c, d, e = self.setup()

        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="date", date_interval="year")),
                         {datetime.datetime(2001, 1, 1): 3, datetime.datetime(2002, 1, 1): 1})

        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="date", date_interval="month")),
                         {datetime.datetime(2001, 1, 1): 1, datetime.datetime(2002, 1, 1): 1, datetime.datetime(2001, 2, 1): 2})

        # set statistics
        stats = ES().statistics(filters=dict(sets=s1.id))
        self.assertEqual(stats.n, 4)
        self.assertEqual(stats.start_date, datetime.datetime(2001, 1, 1))
        self.assertEqual(stats.end_date, datetime.datetime(2002, 1, 1))


    @amcattest.use_elastic
    def test_terms_aggregate(self):
        s1, s2, a, b, c, d, e = self.setup()
        q1 = SearchQuery.from_string("noot")
        q2 = SearchQuery.from_string("bla")

        query = lambda **kw: ES().aggregate_query(filters={"sets": s1.id}, **kw)

        # Should raise error if not terms are supplied
        self.assertRaises(ValueError, query, group_by=["terms"])

        # Should convert terms to 'buckets'
        aggr = query(group_by=["terms"], terms=[q1, q2])
        self.assertEqual(set(aggr), {(q1, 3), (q2, 1)})

    @amcattest.use_elastic
    def test_sets_aggregate(self):
        s1, s2, a, b, c, d, e = self.setup()

        query = lambda **kw: set(ES().aggregate_query(filters={"sets": [s1.id, s2.id]}, **kw))

        # Not specifiying a 'filter' should result in all sets
        self.assertEqual(query(group_by=["sets"]), {(s1.id, 4), (s2.id, 1)})

        # Specifiying a 'filter' should result in less sets
        self.assertEqual(query(group_by=["sets"], sets=[s1.id]), {(s1.id, 4)})


    @amcattest.use_elastic
    def test_query_all(self):
        """Test that query_all works"""
        from amcat.models import Article
        arts = [amcattest.create_test_article(create=False) for _ in range(20)]
        s = amcattest.create_test_set()
        Article.create_articles(arts, articleset=s)
        ES().flush()

        r = ES().query(filters=dict(sets=s.id), size=10)
        self.assertEqual(len(list(r)), 10)

        r = ES().query_all(filters=dict(sets=s.id), size=10)
        self.assertEqual(len(list(r)), len(arts))


    @amcattest.use_elastic
    def test_filters(self):
        """
        Do filters work properly?
        """
        a = amcattest.create_test_article(text='aap noot mies', title='m1', date="2001-01-01")
        b = amcattest.create_test_article(text='noot mies wim zus', title='m2', date="2002-01-01")
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', title='m2', date="2003-01-01")

        s1 = amcattest.create_test_set(articles=[a, b, c])
        s2 = amcattest.create_test_set(articles=[a, b])
        ES().flush()

        q = lambda **filters: set(ES().query_ids(filters=filters))

        # TITLE FILTER
        self.assertEqual(q(title='m2'), {b.id, c.id})

        #### DATE FILTERS
        self.assertEqual(q(sets=s1.id, start_date='2001-06-01'), {b.id, c.id})
        # start is inclusive
        self.assertEqual(q(sets=s1.id, start_date='2002-01-01', end_date="2002-06-01"), {b.id})
        # end is exclusive
        self.assertEqual(q(sets=s1.id, start_date='2001-01-01', end_date="2003-01-01"), {a.id, b.id})

        # COMBINATION
        self.assertEqual(q(sets=s2.id, start_date='2001-06-01'), {b.id})
        self.assertEqual(q(end_date='2002-06-01', title='m2'), {b.id})

    @amcattest.use_elastic
    def test_query(self):
        """Do query and query_ids work properly?"""
        a = amcattest.create_test_article(title="bla", text="artikel artikel een", date="2001-01-01")
        ES().flush()
        es_a, = ES().query("een", fields=["date", "title"])
        self.assertEqual(es_a.title, "bla")
        self.assertEqual(es_a.id, a.id)
        ids = set(ES().query_ids(filters=dict(title='bla')))
        self.assertEqual(ids, {a.id})


    @amcattest.use_elastic
    def test_articlesets(self):
        a, b, c = [amcattest.create_test_article() for _x in range(3)]
        s1 = amcattest.create_test_set(articles=[a, b, c])
        s2 = amcattest.create_test_set(articles=[b, c])
        s3 = amcattest.create_test_set(articles=[b])
        ES().flush()

        es_c = ES().get(c.id)
        self.assertEqual(set(es_c['sets']), {s1.id, s2.id})

        ids = ES().query_ids(filters=dict(sets=s1.id))
        self.assertEqual(set(ids), {a.id, b.id, c.id})

    @amcattest.use_elastic
    def test_refresh_index(self):
        """Are added/removed articles added/removed from the index?"""
        # TODO add/remove articles adds to index automatically (does remove?)
        # so refresh isn't really used. Rewrite to add to db manually
        s = amcattest.create_test_set()
        a = amcattest.create_test_article()

        s.add_articles([a.id], add_to_index=False)
        self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s.id))))
        s.refresh_index()
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s.id))))

        # check adding of existing articles to a new set:
        s2 = amcattest.create_test_set()
        s2.add(a)
        s2.refresh_index()
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s2.id))))
        # check that removing of articles from a set works and does not affect
        # other sets
        s2.remove_articles([a])
        s2.refresh_index()
        self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s2.id))))
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s.id))))

        s.remove_articles([a], remove_from_index=False)
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s.id))))
        s.refresh_index()
        self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s.id))))

        # test that remove from index works for larger sets
        s = amcattest.create_test_set()
        arts = [amcattest.create_test_article() for i in range(20)]
        s.add(*arts)

        s.refresh_index()
        solr_ids = set(ES().query_ids(filters=dict(sets=s.id)))
        self.assertEqual(set(solr_ids), {a.id for a in arts})

        s.remove_articles([arts[0]])
        s.remove_articles([arts[-1]])
        s.refresh_index()
        solr_ids = set(ES().query_ids(filters=dict(sets=s.id)))
        self.assertEqual(set(solr_ids), {a.id for a in arts[1:-1]})


    @amcattest.use_elastic
    def test_full_refresh(self):
        """test full refresh, e.g. document content change"""
        a = amcattest.create_test_article(text='aap noot mies', title='m1')
        s = amcattest.create_test_set()
        s.add(a)
        s.refresh_index()
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, title='m1'))), {a.id})

        a.title='m2'
        a.save()
        s.refresh_index(full_refresh=False)  # a should NOT be reindexed
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, title='m1'))), {a.id})
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, title='m2'))), set())

        s.refresh_index(full_refresh=True)
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, title='m1'))), set())
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, title='m2'))), {a.id})

    @amcattest.use_elastic
    def test_scores(self):
        """test if scores (and matches) are as expected for various queries"""
        s = amcattest.create_test_set(articles=[
            amcattest.create_test_article(title="a", text='dit is een test'),
        ])

        s.refresh_index()

        def q(query):
            result = ES().query(query, filters={'sets': s.id}, fields=["title"])
            return {a.title: a.score for a in result}

        self.assertEqual(q("test"), {"a": 1})

        a = amcattest.create_test_article(text='aap noot mies', title='m1')
        b = amcattest.create_test_article(text='noot mies wim zus', title='m2')
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', title='m2')
        d = amcattest.create_test_article(text='ik woon in een sociale huurwoning, net als anderen', title='m2')
        ES().flush()

        self.assertEqual(set(ES().query_ids("no*")), {a.id, b.id})
        self.assertEqual(set(ES().query_ids("no*", filters=dict(title='m2'))), {b.id})
        self.assertEqual(set(ES().query_ids("zus AND jet", filters=dict(title='m2'))), {c.id})
        self.assertEqual(set(ES().query_ids("zus OR jet", filters=dict(title='m2'))), {b.id, c.id})
        self.assertEqual(set(ES().query_ids('"mies wim"', filters=dict(title='m2'))), {b.id})
        self.assertEqual(set(ES().query_ids('"mies wim"~5', filters=dict(title='m2'))), {b.id, c.id})

        self.assertEqual(set(ES().query_ids('"sociale huur*"', filters=dict(title='m2'))), {d.id})
        self.assertEqual(set(ES().query_ids('"sociale huur*"', filters=dict(title='m2'))), {d.id})


    @amcattest.use_elastic
    def test_complex_phrase_query(self):
        """Test complex phrase queries. DOES NOT WORK YET"""
        a = amcattest.create_test_article(text='aap noot mies')
        b = amcattest.create_test_article(text='noot mies wim zus')
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet')
        s1 = amcattest.create_test_set(articles=[a, b, c])
        ES().flush()
        self.assertEqual(set(ES().query_ids('"mi* wi*"~5', filters=dict(sets=s1.id))), {b.id, c.id})


    @amcattest.use_elastic
    def test_tokenizer(self):
        text = "Rutte's Fu\xdf.d66,  50plus, 50+, el ni\xf1o, kanji (\u6f22\u5b57) en Noord-Korea"
        a = amcattest.create_test_article(title="test", text=text)
        s1 = amcattest.create_test_set(articles=[a])

        ES().flush()
        self.assertEqual(set(ES().query_ids("kanji", filters=dict(sets=s1.id))), {a.id})
        self.assertEqual(set(ES().query_ids("blablabla", filters=dict(sets=s1.id))), set())

        # test noord-korea --> noord korea
        self.assertEqual(set(ES().query_ids("korea", filters=dict(sets=s1.id))), {a.id})
        self.assertEqual(set(ES().query_ids('"korea-noord"', filters=dict(sets=s1.id))), set())
        self.assertEqual(set(ES().query_ids('"noord-korea"', filters=dict(sets=s1.id))), {a.id})

        # test Rutte's -> rutte s
        self.assertEqual(set(ES().query_ids("rutte", filters=dict(sets=s1.id))), {a.id})
        self.assertEqual(set(ES().query_ids("Rutte", filters=dict(sets=s1.id))), {a.id})

        # test ni\~no -> nino
        self.assertEqual(set(ES().query_ids("nino", filters=dict(sets=s1.id))), {a.id})
        self.assertEqual(set(ES().query_ids("ni\xf1o", filters=dict(sets=s1.id))), {a.id})

        # test real kanji
        self.assertEqual(set(ES().query_ids("\u6f22\u5b57", filters=dict(sets=s1.id))), {a.id})

    @amcattest.use_elastic
    def test_title(self):
        aset = amcattest.create_test_set()
        amcattest.create_test_article(title="bob", text="eve", articleset=aset)

        ES().flush()

        q = lambda query: set(ES().query_ids(query, filters={"sets": aset.id}))

        self.assertEqual(1, len(q("title:bob")))
        self.assertEqual(0, len(q("title:eve")))
        self.assertEqual(1, len(q("bob")))

    @amcattest.use_elastic
    def test_not(self):
        aset = amcattest.create_test_set()
        eve = amcattest.create_test_article(text="eve", articleset=aset)
        paul = amcattest.create_test_article(text="paul", articleset=aset)
        adam = amcattest.create_test_article(text="adam", articleset=aset)

        ES().flush()

        q = lambda query: set(ES().query_ids(query, filters={"sets": aset.id}))

        self.assertEqual({eve.id}, q("eve"))
        self.assertEqual({paul.id, adam.id}, q("NOT eve"))
        self.assertEqual({paul.id, adam.id}, q("* NOT eve"))
        self.assertEqual({eve.id}, q("NOT (NOT eve)"))

    @amcattest.use_elastic
    def test_elastic_hash(self):
        """Can we reproduce a hash from elastic data alone?"""
        article = Article(**{
            "date": datetime.date(2015, 1, 1),
            "title": "\u6f22\u5b57",
            "text": "Even more strange characters.. \x0C and \x08 woo?",
            "url": "https://example.com",
            "project": create_test_project()
        })

        hash = get_article_dict(article)['hash']
        Article.create_articles([article], articleset=amcattest.create_test_set())
        ES().flush()
        es_articles = ES().query_all(filters={"ids": [article.id]}, fields=["hash"])
        es_articles = list(es_articles)
        es_article = list(es_articles)[0]

        self.assertEqual(article.id, es_article.id)
        self.assertEqual(hash, es_article.hash)
        self.assertEqual(hash, article.hash)

    @amcattest.use_elastic
    def test_properties(self):
        """Are properties stored as flat fields and with correct mapping?"""
        props = dict(
            proptest="123 test, and another",
            proptest2_url="http://example.org",
            proptest3_date="2001-01-01",
            proptest4_num=-1,
            proptest5_tag="123 test, and another",
            proptest6_id="123 test, and another")

        self.assertEqual(set(props.keys()) & set(ES().get_mapping().keys()), set())

        a = amcattest.create_test_article(properties=props)

        mapping = ES().get_mapping()
        for field, ftype in dict(proptest="default", proptest2_url="url",
                                 proptest3_date="date", proptest4_num="num",
                                 proptest5_tag="tag").items():
            self.assertEqual(mapping[field], settings.ES_MAPPING_TYPES[ftype])
            
        src = ES().get(a.id)
        self.assertEqual(set(mapping.keys()), set(props.keys()) | ALL_FIELDS)

        # test if term vectors are correct, i.e. test analysis
        def tokens(field):
            tokens = list(ES().get_tokens(a.id, fields=[field]))
            return [w for (f, p, w) in sorted(tokens)]

        self.assertEqual(tokens("proptest"), ["123", "test", "and", "another"])
        self.assertEqual(tokens("proptest5_tag"), ["123 test", "and another"])
        self.assertEqual(tokens("proptest6_id"), ["123 test, and another"])
        self.assertEqual(tokens("proptest2_url"), ["http://example.org"])

    def test_used_properties(self):
        a1 = amcattest.create_test_article(properties={"p1": "test", "p2_date": "2001-01-01"})
        a2 = amcattest.create_test_article(properties={"p1": "test", "p3_num": 15})
        a3 = amcattest.create_test_article(properties={"p1": "test", "p4": "test"})

        s1 = amcattest.create_test_set(articles=[a1])
        s2 = amcattest.create_test_set(articles=[a2])
        s3 = amcattest.create_test_set(articles=[a1, a3])
        ES().flush()
        self.assertEqual(set(ES().get_used_properties([s1.id])), {"p1", "p2_date"})
        self.assertEqual(set(ES().get_used_properties([s1.id, s2.id])), {"p1", "p2_date", "p3_num"})
        self.assertEqual(set(ES().get_used_properties([s3.id])), {"p1", "p2_date", "p4"})

        self.assertEqual(set(ES().get_used_properties([s1.id])), {"p1", "p2_date"})
        self.assertEqual(set(ES().get_used_properties([s1.id, s2.id])), {"p1", "p2_date", "p3_num"})
        self.assertEqual(set(ES().get_used_properties([s3.id])), {"p1", "p2_date", "p4"})
        
    def test_date(self):
        # Test iso8601 parsing, database parsing, etc.
        iso8601_date_string = '1992-12-31T23:59:00'
        date = datetime.datetime(1992, 12, 31, 23, 59, 0)
        date_parsed = iso8601.parse_date(iso8601_date_string, default_timezone=None)
        a = amcattest.create_test_article(date=iso8601_date_string)
        self.assertEqual(date_parsed, date)
        self.assertEqual(a.date, date)

        ES().flush()

        # Test Elastic date parsing
        es_date = ES().get(a.id)["date"]
        self.assertEqual(es_date, '1992-12-31T23:59:00')
        self.assertEqual(iso8601.parse_date(es_date, None), date)

