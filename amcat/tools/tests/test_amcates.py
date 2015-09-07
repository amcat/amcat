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
from __future__ import unicode_literals

import datetime
from unittest import skip
from amcat.models import Article
from amcat.tools import amcattest
from amcat.tools.amcates import ES, get_article_dict, HASH_FIELDS, _get_hash
from amcat.tools.amcattest import create_test_medium, create_test_project, create_test_set
from amcat.tools.keywordsearch import SearchQuery


class TestAmcatES(amcattest.AmCATTestCase):
    def setup(self):
        m1 = amcattest.create_test_medium(name="De Nep-Krant")
        m2, m3 = [amcattest.create_test_medium() for _ in range(2)]
        s1 = amcattest.create_test_set()
        s2 = amcattest.create_test_set()
        a = amcattest.create_test_article(text='aap noot mies', medium=m1, date='2001-01-01', create=False)
        b = amcattest.create_test_article(text='noot mies wim zus', medium=m2, date='2001-02-01', create=False)
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', medium=m2, date='2002-01-01', create=False)
        d = amcattest.create_test_article(text='noot mies wim zus', medium=m2, date='2001-02-03', create=False)
        e = amcattest.create_test_article(text='aap noot mies', medium=m3, articleset=s2)

        Article.create_articles([a, b, c, d], articleset=s1, check_duplicate=False, create_id=True)
        ES().flush()
        return m1, m2, m3, s1, s2, a, b, c, d, e

    @amcattest.use_elastic
    def test_aggregate(self):
        """Can we make tables per medium/date interval?"""
        m1, m2, m3, s1, s2, a, b, c, d, e = self.setup()

        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="mediumid")),
                         {m1.id: 1, m2.id: 3})

        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="date", date_interval="year")),
                         {datetime.datetime(2001, 1, 1): 3, datetime.datetime(2002, 1, 1): 1})

        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="date", date_interval="month")),
                         {datetime.datetime(2001, 1, 1): 1, datetime.datetime(2002, 1, 1): 1, datetime.datetime(2001, 2, 1): 2})

        # set statistics
        stats = ES().statistics(filters=dict(sets=s1.id))
        self.assertEqual(stats.n, 4)
        self.assertEqual(stats.start_date, datetime.datetime(2001, 1, 1))
        self.assertEqual(stats.end_date, datetime.datetime(2002, 1, 1))

        # media list
        self.assertEqual(set(ES().list_media(filters=dict(sets=s1.id))),
                         {m1.id, m2.id})

    @amcattest.use_elastic
    def test_terms_aggregate(self):
        m1, m2, m3, s1, s2, a, b, c, d, e = self.setup()
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
        m1, m2, m3, s1, s2, a, b, c, d, e = self.setup()

        query = lambda **kw: set(ES().aggregate_query(filters={"sets": [s1.id, s2.id]}, **kw))

        # Not specifiying a 'filter' should result in all sets
        self.assertEqual(query(group_by=["sets"]), {(s1.id, 4), (s2.id, 1)})

        # Specifiying a 'filter' should result in less sets
        self.assertEqual(query(group_by=["sets"], sets=[s1.id]), {(s1.id, 4)})


    @amcattest.use_elastic
    def test_list_media(self):
        """Test that list media works for more than 10 media"""
        from amcat.models import Article

        media = [amcattest.create_test_medium() for _ in range(20)]
        arts = [amcattest.create_test_article(medium=m, create=False) for m in media]

        s1 = amcattest.create_test_set()
        Article.create_articles(arts[:5], articleset=s1, check_duplicate=False, create_id=True)
        ES().flush()
        self.assertEqual(set(s1.get_mediums()), set(media[:5]))

        s2 = amcattest.create_test_set(project=s1.project)
        Article.create_articles(arts[5:], articleset=s2, check_duplicate=False, create_id=True)
        ES().flush()
        self.assertEqual(set(s2.get_mediums()), set(media[5:]))

        self.assertEqual(set(s1.project.get_mediums()), set(media))


    @amcattest.use_elastic
    def test_query_all(self):
        """Test that query_all works"""
        from amcat.models import Article
        arts = [amcattest.create_test_article(create=False) for _ in range(20)]
        s = amcattest.create_test_set()
        Article.create_articles(arts, articleset=s, check_duplicate=False, create_id=True)
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
        m1, m2 = [amcattest.create_test_medium() for _ in range(2)]
        a = amcattest.create_test_article(text='aap noot mies', medium=m1, date="2001-01-01")
        b = amcattest.create_test_article(text='noot mies wim zus', medium=m2, date="2002-01-01")
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', medium=m2, date="2003-01-01")

        s1 = amcattest.create_test_set(articles=[a, b, c])
        s2 = amcattest.create_test_set(articles=[a, b])
        ES().flush()

        q = lambda **filters: set(ES().query_ids(filters=filters))

        # MEDIUM FILTER
        self.assertEqual(q(mediumid=m2.id), {b.id, c.id})

        #### DATE FILTERS
        self.assertEqual(q(sets=s1.id, start_date='2001-06-01'), {b.id, c.id})
        # start is inclusive
        self.assertEqual(q(sets=s1.id, start_date='2002-01-01', end_date="2002-06-01"), {b.id})
        # end is exclusive
        self.assertEqual(q(sets=s1.id, start_date='2001-01-01', end_date="2003-01-01"), {a.id, b.id})

        # COMBINATION
        self.assertEqual(q(sets=s2.id, start_date='2001-06-01'), {b.id})
        self.assertEqual(q(end_date='2002-06-01', mediumid=m2.id), {b.id})

    @amcattest.use_elastic
    def test_query(self):
        """Do query and query_ids work properly?"""
        a = amcattest.create_test_article(headline="bla", text="artikel artikel een", date="2001-01-01")
        ES().flush()
        es_a, = ES().query("een", fields=["date", "headline"])
        self.assertEqual(es_a.headline, "bla")
        self.assertEqual(es_a.id, a.id)
        ids = set(ES().query_ids(filters=dict(mediumid=a.medium_id)))
        self.assertEqual(ids, {a.id})


    @amcattest.use_elastic
    def test_articlesets(self):
        a, b, c = [amcattest.create_test_article() for _x in range(3)]
        s1 = amcattest.create_test_set(articles=[a, b, c])
        s2 = amcattest.create_test_set(articles=[b, c])
        s3 = amcattest.create_test_set(articles=[b])
        ES().add_articles([a.id, b.id, c.id])
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

        s.add(a)
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
        arts = [amcattest.create_test_article(medium=a.medium) for i in range(20)]
        s.add(*arts)

        s.refresh_index()
        solr_ids = set(ES().query_ids(filters=dict(sets=s.id)))
        self.assertEqual(set(solr_ids), {a.id for a in arts})

        s.remove_articles([arts[0]])
        s.remove_articles([arts[-1]])
        s.refresh_index()
        solr_ids = set(ES().query_ids(filters=dict(sets=s.id)))
        self.assertEqual(set(solr_ids), {a.id for a in arts[1:-1]})

        # test that changing an article's properties can be reindexed
        arts[1].medium = amcattest.create_test_medium()
        arts[1].save()


    @amcattest.use_elastic
    def test_full_refresh(self):
        """test full refresh, e.g. document content change"""
        m1, m2 = [amcattest.create_test_medium() for _ in range(2)]
        a = amcattest.create_test_article(text='aap noot mies', medium=m1)
        s = amcattest.create_test_set()
        s.add(a)
        s.refresh_index()
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=m1.id))), {a.id})

        a.medium = m2
        a.save()
        s.refresh_index(full_refresh=False)  # a should NOT be reindexed
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=m1.id))), {a.id})
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=m2.id))), set())

        s.refresh_index(full_refresh=True)
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=m1.id))), set())
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=m2.id))), {a.id})

    @amcattest.use_elastic
    def test_scores(self):
        """test if scores (and matches) are as expected for various queries"""
        s = amcattest.create_test_set(articles=[
            amcattest.create_test_article(headline="a", text='dit is een test'),
        ])

        s.refresh_index()

        def q(query):
            result = ES().query(query, filters={'sets': s.id}, fields=["headline"])
            return {a.headline: a.score for a in result}

        self.assertEqual(q("test"), {"a": 1})

        m1, m2 = [amcattest.create_test_medium() for _ in range(2)]
        a = amcattest.create_test_article(text='aap noot mies', medium=m1)
        b = amcattest.create_test_article(text='noot mies wim zus', medium=m2)
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', medium=m2)
        d = amcattest.create_test_article(text='ik woon in een sociale huurwoning, net als anderen', medium=m2)
        ES().flush()

        self.assertEqual(set(ES().query_ids("no*")), {a.id, b.id})
        self.assertEqual(set(ES().query_ids("no*", filters=dict(mediumid=m2.id))), {b.id})
        self.assertEqual(set(ES().query_ids("zus AND jet", filters=dict(mediumid=m2.id))), {c.id})
        self.assertEqual(set(ES().query_ids("zus OR jet", filters=dict(mediumid=m2.id))), {b.id, c.id})
        self.assertEqual(set(ES().query_ids('"mies wim"', filters=dict(mediumid=m2.id))), {b.id})
        self.assertEqual(set(ES().query_ids('"mies wim"~5', filters=dict(mediumid=m2.id))), {b.id, c.id})

        self.assertEqual(set(ES().query_ids('"sociale huur*"', filters=dict(mediumid=m2.id))), {d.id})
        self.assertEqual(set(ES().query_ids('"sociale huur*"', filters=dict(mediumid=m2.id))), {d.id})


    @skip("ComplexPhraseQueryParser does not work for elastic")
    def test_complex_phrase_query(self):
        """Test complex phrase queries. DOES NOT WORK YET"""
        a = amcattest.create_test_article(text='aap noot mies')
        b = amcattest.create_test_article(text='noot mies wim zus')
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet')
        s1 = amcattest.create_test_set(articles=[a, b, c])
        ES().add_articles([a.id, b.id, c.id])
        self.assertEqual(set(ES().query_ids('"mi* wi*"~5', filters=dict(sets=s1.id))), {b.id, c.id})


    @amcattest.use_elastic
    def test_tokenizer(self):
        text = u"Rutte's Fu\xdf.d66,  50plus, 50+, el ni\xf1o, kanji (\u6f22\u5b57) en Noord-Korea"
        a = amcattest.create_test_article(headline="test", text=text)
        s1 = amcattest.create_test_set(articles=[a])
        ES().add_articles([a.id])
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
        self.assertEqual(set(ES().query_ids(u"ni\xf1o", filters=dict(sets=s1.id))), {a.id})

        # test real kanji
        self.assertEqual(set(ES().query_ids(u"\u6f22\u5b57", filters=dict(sets=s1.id))), {a.id})

    @amcattest.use_elastic
    def test_byline(self):
        aset = amcattest.create_test_set()
        amcattest.create_test_article(byline="bob", text="eve", articleset=aset)

        ES().flush()

        q = lambda query: set(ES().query_ids(query, filters={"sets": aset.id}))

        self.assertEqual(1, len(q("byline:bob")))
        self.assertEqual(0, len(q("byline:eve")))
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
            "section": "\u6f22\u5b57",
            "pagenr": 1928390,
            "headline": "Headline hier.",
            "byline": "byline..",
            "length": 1928,
            "metastring": "Even more strange characters.. \x0C ..",
            "url": "https://example.com",
            "externalid": None,
            "author": None,
            "addressee": "Hmm",
            "text": "Contains invalid char \x08 woo",
            "medium": create_test_medium(name="abc."),
            "project": create_test_project()
        })

        article.save()

        es = ES()
        es.add_articles([article.id])
        hash = get_article_dict(article)["hash"]
        es.flush()

        es_articles = es.query_all(filters={"ids": [article.id]}, fields=HASH_FIELDS + ["hash"])
        es_article = list(es_articles)[0]

        self.assertEqual(article.id, es_article.id)
        self.assertEqual(hash, es_article.hash)
        self.assertEqual(_get_hash(es_article.to_dict()), hash)
