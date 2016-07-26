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
from amcat.models import Article, word_len, ArticleTree
from amcat.tools import amcattest
from amcat.tools import amcates
from amcat.tools.amcattest import create_test_article, create_test_set

import datetime
import uuid
import random
import binascii

def _setup_highlighting():
    from amcat.tools.amcates import ES

    article = create_test_article(text="<p>foo</p>", headline="<p>bar</p>")
    ES().flush()
    return article


class TestArticleHighlighting(amcattest.AmCATTestCase):
    @amcattest.use_elastic
    def test_defaults(self):
        """Test if default highlighting works."""
        article = _setup_highlighting()
        article.highlight("foo")
        self.assertEqual("&lt;p&gt;<em>foo</em>&lt;/p&gt;", article.text)
        self.assertEqual("&lt;p&gt;bar&lt;/p&gt;", article.headline)

    @amcattest.use_elastic
    def test_no_escape(self):
        article = _setup_highlighting()
        article.highlight("foo", escape=False)
        self.assertEqual("<p><em>foo</em></p>", article.text)
        self.assertEqual("<p>bar</p>", article.headline)

    @amcattest.use_elastic
    def test_no_keepem(self):
        article = _setup_highlighting()
        article.highlight("foo", keep_em=False)
        self.assertEqual("&lt;p&gt;&lt;em&gt;foo&lt;/em&gt;&lt;/p&gt;", article.text)
        self.assertEqual("&lt;p&gt;bar&lt;/p&gt;", article.headline)

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
        self.assertEqual("<p>bar</p>", article.headline)



def _q(**filters):
    amcates.ES().flush()
    return set(amcates.ES().query_ids(filters=filters))
    
class TestArticle(amcattest.AmCATTestCase):
    @amcattest.use_elastic
    def test_save_parent(self):
        """Can we save objects with new and existing parents?"""
        m = amcattest.create_test_medium()
        root = create_test_article()
        s = create_test_set()
        structure = {1:0, 2:1, 3:1, 4:0}
        adict= dict(medium=m, date=datetime.date(2001,1,1), project=s.project)
        def _articles(n, structure):
            articles = [Article(headline=str(i), text=str(i), **adict) for i in range(n)]
            articles[0].parent = root
            for child, parent in structure.items():
                articles[child].parent = articles[parent]
            return articles

        # Trees are 3 levels deep, so it should take 3 queries to complete this request
        articles = _articles(5, structure)
        self.assertNumQueries(3, Article.create_articles, articles)

        ids = _q(mediumid=m.id)
        self.assertEqual(len(ids), 5)
        a = {int(a.text):a for a in Article.objects.filter(pk__in=ids)}

        # Are the parent properties set correctly?
        self.assertEqual(a[0].parent, root)        
        for child, parent in structure.items():
            articles[child].parent = articles[parent]
            self.assertEqual(a[child].parent, a[parent])

        # can we save it again without errors? (And without queries, since it's all dupes
        articles = _articles(5, structure)
        self.assertNumQueries(0, Article.create_articles, articles)
        self.assertEqual(len(_q(mediumid=m.id)), 5)
        
        # Can we insert new articles together with dupes?
        structure.update({5:1, 6:1})
        articles = _articles(7, structure)
        articles[6].parent = a[1] # existing article
        amcates.ES().flush()
        # (inefficiency: it knows it can save 6 immediately, doesn't know it can also save 5 until dedup)
        self.assertNumQueries(2, Article.create_articles, articles)
        ids = _q(mediumid=m.id)
        self.assertEqual(len(ids), 7)
        a = {int(a.text):a for a in Article.objects.filter(pk__in=ids)}
        self.assertEqual(a[0].parent, root)        
        for child, parent in structure.items():
            articles[child].parent = articles[parent]
            self.assertEqual(a[child].parent, a[parent])
        #TODO: WvA: test errors on external unsaved parents and cycles
        
        
        
    @amcattest.use_elastic
    def test_create(self):
        """Can we create/store/index an article object?"""
        a = amcattest.create_test_article(create=False, date='2010-12-31', title=u'\ua000abcd\u07b4')
        Article.create_articles([a])
        db_a = Article.objects.get(pk=a.id)
        amcates.ES().flush()
        es_a = list(amcates.ES().query(filters={'ids': [a.id]}, fields=["date", "title", "hash"]))[0]
        self.assertEqual(bytes(a.hash), bytes(db_a.hash))
        self.assertEqual(bytes(a.hash), binascii.unhexlify(es_a.hash))
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
        
        art = dict(headline="test", text="test", byline="test", date='2001-01-01',
                   medium=amcattest.create_test_medium(),
                   project=amcattest.create_test_project(),
                   )
        a1 = amcattest.create_test_article(**art)
        amcates.ES().flush()
        self.assertEqual(_q(mediumid=art['medium']), {a1.id})


        # duplicate articles should not be added
        a2 = amcattest.create_test_article(**art)
        amcates.ES().flush()
        self.assertEqual(a2.id, a1.id)
        self.assertTrue(a2.duplicate)
        self.assertEqual(_q(mediumid=art['medium']), {a1.id})

        # however, if an articleset is given the 'existing' article
        # should be added to that set
        s1 = amcattest.create_test_set()
        a3 = amcattest.create_test_article(articleset=s1, **art)
        amcates.ES().flush()
        self.assertEqual(a3.id, a1.id)
        self.assertEqual(_q(mediumid=art['medium']), {a1.id})
        self.assertEqual(set(s1.get_article_ids()), {a1.id})
        self.assertEqual(_q(sets=s1.id), {a1.id})

        # a dupe with a non-identical uuid is not a dupe
        uu = uuid.uuid4()
        a4 = amcattest.create_test_article(uuid=uu, **art)
        self.assertFalse(a4.duplicate)
        self.assertEqual(a4.uuid, uu)
        
        # if an existing uuid is set, it should be a perfect duplicate
        art['uuid'] = a1.uuid
        a5 = amcattest.create_test_article(**art) # okay
        amcates.ES().flush()
        self.assertEqual(_q(mediumid=art['medium']), {a1.id, a4.id}) # a5 is a dupe
        
        art['headline']="not the same"
        self.assertRaises(ValueError, amcattest.create_test_article, **art) # not okay

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
        # do the right articles have the right headline?
        for saved in articles:
            indb = Article.objects.get(pk=saved.id)
            self.assertEqual(indb.title, saved.title)


    @amcattest.use_elastic
    def test_str(self):
        """Test unicode headlines"""
        for offset in range(1, 10000, 1000):
            s = "".join(chr(offset + c) for c in range(1, 1000, 100))
            a = amcattest.create_test_article(title=s)
            self.assertIsInstance(a.title, str)
            self.assertEqual(a.title, s)


    @amcattest.use_elastic
    def test_get_tree(self):
        article1 = amcattest.create_test_article()
        self.assertEqual(article1.get_tree(), ArticleTree(article1, []))

        # Equals does not compare nested
        article2 = amcattest.create_test_article(parent=article1)
        self.assertEqual(
            article1.get_tree(),
            ArticleTree(article1, [ArticleTree(article2, [])])
        )

        # Test default include_parent = True
        self.assertEqual(
            article2.get_tree(),
            ArticleTree(article1, [ArticleTree(article2, [])])
        )

        # Test include_parents = False
        self.assertEqual(
            article2.get_tree(include_parents=False),
            ArticleTree(article2, [])
        )


class TestArticleTree(amcattest.TestCase):
    def test_get_ids(self):
        tree = ArticleTree(
            Article(id=3), [
                ArticleTree(Article(id=5), []), ArticleTree(Article(id=6), [
                    ArticleTree(Article(id=7), [])
                ])
            ]
        )

        self.assertEqual({3, 5, 6, 7}, set(tree.get_ids()))
