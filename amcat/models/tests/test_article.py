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
from iso8601.iso8601 import UTC

from amcat.models.article import get_used_properties
from amcat.models import Article, word_len
from amcat.models import PropertyMapping
from amcat.tools import amcattest
from amcat.tools import amcates
from amcat.tools.amcattest import create_test_article

import datetime
import random

def _setup_highlighting():
    from amcat.tools.amcates import ES

    article = create_test_article(text="<p>foo</p>", title="<p>bar</p>")
    ES().flush()
    return article


class TestProperties(amcattest.AmCATTestCase):
    def test_get_used_properties(self):
        a1 = amcattest.create_test_article(properties={"aap": "noot", "jan": "mies"})
        a2 = amcattest.create_test_article(properties={"vuur": "paal"})

        self.assertEqual(set(get_used_properties([a1.id])), {"aap", "jan"})
        self.assertEqual(set(get_used_properties([a2.id])), {"vuur"})
        self.assertEqual(set(get_used_properties([a1.id, a2.id])), {"vuur", "aap", "jan"})

    def test_default(self):
        self.assertEqual(PropertyMapping, type(Article().properties))

    def test_save(self):
        a = create_test_article()

        now = datetime.datetime.now(tz=UTC)
        a.properties["now_date"] = now
        a.properties["progress_num"] = 3.6
        a.properties["length_int"] = 3
        a.save()

        a = Article.objects.first()

        self.assertEqual(a.get_property("now_date"), now)
        self.assertEqual(a.get_property("progress_num"), 3.6)
        self.assertEqual(a.get_property("length_int"), 3)

        self.assertEqual(a.properties["now_date"], now)
        self.assertEqual(a.properties["progress_num"], 3.6)
        self.assertEqual(a.properties["length_int"], 3)

    def test_illegal_assignments(self):
        a = create_test_article()

        # Test datetype
        self.assertRaises(ValueError, a.set_property, "now_date", "a")
        self.assertRaises(ValueError, a.set_property, "now_date", 3)
        self.assertRaises(ValueError, a.set_property, "now_date", 3.5)
        a.set_property("now_date", datetime.datetime.now())

        # Test float
        self.assertRaises(ValueError, a.set_property, "now_num", "a")
        self.assertRaises(ValueError, a.set_property, "now_num", datetime.datetime.now())
        a.set_property("now_num", .35)

        # Test default
        self.assertRaises(ValueError, a.set_property, "now", .305)
        self.assertRaises(ValueError, a.set_property, "now", 3)
        self.assertRaises(ValueError, a.set_property, "now", datetime.datetime.now())
        a.set_property("now", "test")

    def test_update(self):
        args = {
            "test_num": 3.6,
            "test_int": 3,
            "test": "abc",
            "date": datetime.datetime.now(tz=UTC)
        }

        a = create_test_article()
        a.properties.update(args)
        a.save()

        self.assertEqual(dict(Article.objects.first().properties), args)

    def test_illegal_update(self):
        a = create_test_article()
        self.assertRaises(ValueError, a.properties.update, {"date": 3})

    def test_int_float_conversion(self):
        a = create_test_article()
        a.set_property("test_num", 3)
        self.assertEqual(float, type(a.get_property("test_num")))



class TestArticleHighlighting(amcattest.AmCATTestCase):
    @amcattest.use_elastic
    def test_defaults(self):
        """Test if default highlighting works."""
        article = _setup_highlighting()
        article.highlight("foo")
        self.assertEqual("&lt;p&gt;<em>foo</em>&lt;/p&gt;", article.text)
        self.assertEqual("&lt;p&gt;bar&lt;/p&gt;", article.title)

    @amcattest.use_elastic
    def test_no_escape(self):
        article = _setup_highlighting()
        article.highlight("foo", escape=False)
        self.assertEqual("<p><em>foo</em></p>", article.text)
        self.assertEqual("<p>bar</p>", article.title)

    @amcattest.use_elastic
    def test_no_keepem(self):
        article = _setup_highlighting()
        article.highlight("foo", keep_em=False)
        self.assertEqual("&lt;p&gt;&lt;em&gt;foo&lt;/em&gt;&lt;/p&gt;", article.text)
        self.assertEqual("&lt;p&gt;bar&lt;/p&gt;", article.title)

    @amcattest.use_elastic
    def test_save(self):
        article = _setup_highlighting()
        article.highlight("foo")
        self.assertRaises(ValueError, article.save)

    @amcattest.use_elastic
    def test_no_results_query(self):
        article = _setup_highlighting()
        article.highlight("test")
        self.assertEqual("<p>foo</p>", article.text)
        self.assertEqual("<p>bar</p>", article.title)



def _q(**filters):
    amcates.ES().flush()
    return set(amcates.ES().query_ids(filters=filters))
    
class TestArticle(amcattest.AmCATTestCase):
    @amcattest.use_elastic
    def test_create(self):
        """Can we create/store/index an article object?"""
        a = amcattest.create_test_article(create=False, date='2010-12-31', title=u'\ua000abcd\u07b4')
        Article.create_articles([a])
        db_a = Article.objects.get(pk=a.id)
        amcates.ES().flush()
        es_a = list(amcates.ES().query(filters={'ids': [a.id]}, fields=["date", "title", "hash"]))[0]
        self.assertEqual(a.hash, db_a.hash)
        self.assertEqual(a.hash, es_a.hash)
        self.assertEqual(a.title, db_a.title)
        self.assertEqual(a.title, es_a.title)
        self.assertEqual('2010-12-31T00:00:00', db_a.date.isoformat())
        self.assertEqual('2010-12-31T00:00:00', es_a.date.isoformat())

    @amcattest.use_elastic
    def test_deduplication(self):
        """Does deduplication work as it is supposed to?"""

        # create dummy articles to have something in the db 
        [amcattest.create_test_article() for i in range(10)]
        amcates.ES().flush()
        
        art = dict(project=amcattest.create_test_project(),
                   title="deduptest", text="test", date='2001-01-01')

        a1 = amcattest.create_test_article(**art)
        amcates.ES().flush()
        self.assertEqual(_q(title='deduptest'), {a1.id})

        # duplicate articles should not be added
        a2 = amcattest.create_test_article(**art)
        amcates.ES().flush()
        self.assertEqual(a2.id, a1.id)
        self.assertTrue(a2._duplicate)
        self.assertEqual(_q(title='deduptest'), {a1.id})

        # however, if an articleset is given the 'existing' article
        # should be added to that set
        s1 = amcattest.create_test_set()
        a3 = amcattest.create_test_article(articleset=s1, **art)
        amcates.ES().flush()
        self.assertEqual(a3.id, a1.id)
        self.assertEqual(_q(title='deduptest'), {a1.id})
        self.assertEqual(set(s1.get_article_ids()), {a1.id})
        self.assertEqual(_q(sets=s1.id), {a1.id})

        # if an existing hash is set, it should be correct
        art2 = dict(hash=b'hash', **art)
        self.assertRaises(ValueError, amcattest.create_test_article, **art2)

        #TODO! Check duplicates within new articles
        art['title'] = "internaldupe"
        a1, a2 = (Article(**art), Article(**art))
        Article.create_articles([a1, a2], articleset=s1)
        self.assertEqual(a1.id, a2.id)
        self.assertEqual(len(_q(title='internaldupe')), 1)

    def test_unicode_word_len(self):
        """Does the word counter eat unicode??"""
        u = u'Kim says: \u07c4\u07d0\u07f0\u07cb\u07f9'
        self.assertEqual(word_len(u), 3)

        b = b'Kim did not say: \xe3\xe3k'
        self.assertEqual(word_len(b), 5)

    @amcattest.use_elastic
    def test_create_order(self):
        """Is insert order preserved in id order?"""
        articles = [amcattest.create_test_article(create=False) for _i in range(25)]
        random.shuffle(articles)
        Article.create_articles(articles)
        ids = [a.id for a in articles]
        # is order preserved?
        self.assertEqual(ids, sorted(ids))
        # do the right articles have the right title?
        for saved in articles:
            indb = Article.objects.get(pk=saved.id)
            self.assertEqual(indb.title, saved.title)


    @amcattest.use_elastic
    def test_str(self):
        """Test unicode titles"""
        for offset in range(1, 10000, 1000):
            s = "".join(chr(offset + c) for c in range(1, 1000, 100))
            a = amcattest.create_test_article(title=s)
            self.assertIsInstance(a.title, str)
            self.assertEqual(a.title, s)


    @amcattest.use_elastic
    def test_family(self):
        p = amcattest.create_test_article()
        self.assertEqual(p.parent, None)
        self.assertEqual(set(p.children), set())

        c1 = amcattest.create_test_article(parent_hash=p.hash)
        c2 = amcattest.create_test_article(parent_hash=p.hash)
        
        self.assertEqual(c1.parent, p)
        self.assertEqual(set(p.children), {c1, c2})
