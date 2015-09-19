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
from amcat.tools.amcattest import create_test_article


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


class TestArticle(amcattest.AmCATTestCase):
    def test_save_trees(self):
        articles = [create_test_article(create=False, length=0, headline=str(i)) for i in range(10)]

        tree1 = (articles[0], [
            (articles[1], [
                (articles[2], []),
                (articles[3], [])
            ]),
            (articles[4], [])
        ])

        tree2 = (articles[5], [
            (articles[6], [
                (articles[7], []),
                (articles[8], [])
            ]),
            (articles[9], [])
        ])

        tree1 = ArticleTree.from_tuples(tree1)
        tree2 = ArticleTree.from_tuples(tree2)

        # Trees are 3 levels deep, so it should take 3 queries to complete this request
        self.assertNumQueries(3, Article.save_trees, [tree1, tree2])

        articles = [Article.objects.get(headline=str(i)) for i in range(10)]

        # Is the hierachy / order preserved?
        self.assertEqual(tree1.obj, articles[0])
        self.assertEqual(tree1.children[0].obj, articles[1])
        self.assertEqual(tree1.children[0].children[0].obj, articles[2])
        self.assertEqual(tree1.children[0].children[1].obj, articles[3])
        self.assertEqual(tree1.children[1].obj, articles[4])

        self.assertEqual(tree2.obj, articles[5])
        self.assertEqual(tree2.children[0].obj, articles[6])
        self.assertEqual(tree2.children[0].children[0].obj, articles[7])
        self.assertEqual(tree2.children[0].children[1].obj, articles[8])
        self.assertEqual(tree2.children[1].obj, articles[9])

        # Are the parent properties set correctly?
        self.assertEqual(tree1.parent, None)
        self.assertEqual(tree1.children[0].parent.obj, articles[0])
        self.assertEqual(tree1.children[0].children[0].parent.obj, articles[1])
        self.assertEqual(tree1.children[0].children[1].parent.obj, articles[1])
        self.assertEqual(tree1.children[1].parent.obj, articles[0])

        self.assertEqual(tree2.parent, None)
        self.assertEqual(tree2.children[0].parent.obj, articles[5])
        self.assertEqual(tree2.children[0].children[0].parent.obj, articles[6])
        self.assertEqual(tree2.children[0].children[1].parent.obj, articles[6])
        self.assertEqual(tree2.children[1].parent.obj, articles[5])

    @amcattest.use_elastic
    def test_create(self):
        """Can we create/store/index an article object?"""
        a = amcattest.create_test_article(create=False, date='2010-12-31', headline=u'\ua000abcd\u07b4')
        Article.create_articles([a], create_id=True)
        db_a = Article.objects.get(pk=a.id)
        amcates.ES().flush()
        es_a = list(amcates.ES().query(filters={'ids': [a.id]}, fields=["date", "headline"]))[0]
        self.assertEqual(a.headline, db_a.headline)
        self.assertEqual(a.headline, es_a.headline)
        self.assertEqual('2010-12-31T00:00:00', db_a.date.isoformat())
        self.assertEqual('2010-12-31T00:00:00', es_a.date.isoformat())


    @amcattest.use_elastic
    def test_deduplication(self):
        """Does deduplication work as it is supposed to?"""
        art = dict(headline="test", byline="test", date='2001-01-01',
                   medium=amcattest.create_test_medium(),
                   project=amcattest.create_test_project(),
                   )

        a1 = amcattest.create_test_article(**art)

        def q(**filters):
            amcates.ES().flush()
            return set(amcates.ES().query_ids(filters=filters))

        self.assertEqual(q(mediumid=art['medium']), {a1.id})

        # duplicate articles should not be added
        a2 = amcattest.create_test_article(check_duplicate=True, **art)
        self.assertEqual(a2.id, a1.id)
        self.assertTrue(a2.duplicate)
        self.assertEqual(q(mediumid=art['medium']), {a1.id})

        # however, if an articleset is given the 'existing' article
        # should be added to that set
        s1 = amcattest.create_test_set()
        a3 = amcattest.create_test_article(check_duplicate=True, articleset=s1, **art)
        self.assertEqual(a3.id, a1.id)
        self.assertEqual(q(mediumid=art['medium']), {a1.id})

        self.assertEqual(set(s1.get_article_ids()), {a1.id})
        self.assertEqual(q(sets=s1.id), {a1.id})

        # can we suppress duplicate checking?
        a4 = amcattest.create_test_article(check_duplicate=False, **art)
        self.assertTrue(Article.objects.filter(pk=a4.id).exists())
        self.assertFalse(a4.duplicate)
        self.assertIn(a4.id, q(mediumid=art['medium']))


    def test_unicode_word_len(self):
        """Does the word counter eat unicode??"""
        u = u'Kim says: \u07c4\u07d0\u07f0\u07cb\u07f9'
        self.assertEqual(word_len(u), 3)

        b = b'Kim did not say: \xe3\xe3k'
        self.assertEqual(word_len(b), 5)

    @amcattest.use_elastic
    def test_unicode(self):
        """Test unicode headlines"""
        for offset in range(1, 10000, 1000):
            s = "".join(unichr(offset + c) for c in range(1, 1000, 100))
            a = amcattest.create_test_article(headline=s)
            self.assertIsInstance(a.headline, unicode)
            self.assertEqual(a.headline, s)

    @amcattest.use_elastic
    def test_medium_name(self):
        m = amcattest.create_test_medium(name="de testkrant")
        a = amcattest.create_test_article(medium=m)
        r = amcates.ES().query(filters={"id": a.id}, fields=["medium"])
        print(r)

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
