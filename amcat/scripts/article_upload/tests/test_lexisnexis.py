
import datetime
from amcat.models import ArticleSet
from amcat.scripts.article_upload.lexisnexis import split_header, split_body, parse_header, \
    parse_article, body_to_article, get_query, LexisNexis
from amcat.tools import amcattest


class TestLexisNexis(amcattest.AmCATTestCase):
    def setUp(self):
        import os.path, json

        self.dir = os.path.join(os.path.dirname(__file__), 'test_files', 'lexisnexis')

        self.test_text = open(os.path.join(self.dir, 'test.txt'), encoding="utf-8").read()
        self.test_text2 = open(os.path.join(self.dir, 'test2.txt'), encoding="utf-8").read()
        self.test_text3 = open(os.path.join(self.dir, 'test3.txt'), encoding="utf-8").read()

        self.test_body_sols = json.load(open(os.path.join(self.dir, 'test_body_sols.json')))
        self.test_header_sols = json.load(open(os.path.join(self.dir, 'test_header_sols.json')))

    def test_kop_as_headline(self):
        # Some lexis nexis files contain "KOP: " instaed of "HEADLINE: "
        header, body = split_header(self.test_text3)
        article = body_to_article(*parse_article(next(split_body(body))))
        self.assertEqual("Gretta Duisenberg oprichtster van Palestina-groep", article.headline)

    def split(self):
        return split_header(self.test_text)

    def test_split_header(self):
        splitted = self.split()

        self.assertEquals(len(splitted[0]), 438)

    def test_split_body(self):
        splitted = self.split()

        n_found = len(list(split_body(splitted[1])))
        n_sol = len(self.test_body_sols)

        self.assertEquals(n_found, n_sol + 1)  # +1 for 'defigured' article

    def test_parse_header(self):
        splitted = self.split()

        self.maxDiff = None
        meta = parse_header(splitted[0])
        self.assertEquals(meta, self.test_header_sols)

    def test_parse_article(self):
        splitted = self.split()
        texts = split_body(splitted[1])

        # Json doesn't do dates
        arts = []

        for a in texts:
            art = parse_article(a)
            if art is not None:
                art = list(art)
                art[3] = str(art[3])
                arts.append(art)

        # Tests..
        self.assertEquals(len(arts), len(self.test_body_sols))

        for i, art in enumerate(self.test_body_sols):
            self.assertEquals(art, arts[i])

    def test_meta(self):

        a = list(split_body(self.split()[1]))[0]
        meta = parse_article(a)[-1]
        self.assertEqual(meta.pop('length').split()[0], "306")

    def test_body_to_article(self):
        header, body = self.split()
        articles = split_body(body)
        articles = [parse_article(a) for a in articles]

        # Only testing the first article. If this contains correct
        # data, we assume the implementation is correct. However,
        # we do test the remaining articles with full_clean().

        art = body_to_article(*articles[0])
        self.assertEquals(art.length, 306)
        self.assertEquals(art.headline, "This is a headline")
        self.assertEquals(art.byline, ("with a byline. The article "
                                       "contains unicode characters."))
        self.assertEquals(art.text, articles[0][2])
        self.assertEquals(art.date, datetime.datetime(2011, 8, 31))
        self.assertEquals(art.medium.name, u"B\u00f6rsen-Zeitung")
        self.assertEquals(art.author, "MF Tokio")
        self.assertEquals(eval(art.metastring),
                          {u'update': u'2. September 2011',
                           u'language': u'GERMAN; DEUTSCH',
                           u'publication-type': u'Zeitung'})

        # Setup environment
        dp = amcattest.create_test_project()

        # Test remaining articles
        for art in articles[1:]:
            if art is None: continue

            p = body_to_article(*art)
            p.project = dp
            p.full_clean()

    def test_get_query(self):
        header, body = split_header(self.test_text)
        q = get_query(parse_header(header))
        query = (u'(((Japan OR Fukushima) AND (Erdbeben OR nuklear OR Tsunami'
                 ' OR Krise\nOR Katastrophe OR Tepco)) '
                 ' AND date(geq(7/3/2011) AND leq(31/8/2011)) AND\n'
                 'pub(B\xf6rsen Zeitung OR  Frankfurter Rundschau OR  '
                 'taz OR  die tageszeitung))')
        self.assertEqual(q, query)

        header, body = split_header(self.test_text2)
        q = get_query(parse_header(header))
        self.assertIsNone(q)

    def test_parse_no_header(self):
        header, body = split_header(self.test_text2)
        header = header.replace(u'\ufeff', '').strip()
        self.assertFalse(bool(header))

        n_found = len(list(split_body(body)))
        self.assertEqual(n_found, 1)

    @amcattest.use_elastic
    def test_provenance(self):
        import os.path
        from django.core.files import File

        articleset = amcattest.create_test_set()
        ln = LexisNexis(project=amcattest.create_test_project().id,
                        file=File(open(os.path.join(self.dir, 'test.txt'), "rb")),
                        articlesets=[articleset.id])

        arts = list(ArticleSet.objects.get(id=ln.run()[0]).articles.all())
        self.assertEqual(len(arts), len(self.test_body_sols))
        self.assertIn("LexisNexis query: '(((Japan OR Fukushima)", ln.articlesets[0].provenance)

        articleset = amcattest.create_test_set()
        ln = LexisNexis(project=amcattest.create_test_project().id,
                        file=File(open(os.path.join(self.dir, 'test2.txt'), "rb")),
                        articlesets=[articleset.id])

        arts = ln.run()
        # no query so provenance is the 'standard' message
        self.assertTrue(ln.articlesets[0].provenance.endswith("test2.txt' using LexisNexis"))
