
import datetime
import json

from django.core.files import File

from amcat.models import ArticleSet
from amcat.scripts.article_upload.lexisnexis import split_header, split_body, parse_header, \
    parse_article, get_query, LexisNexis
from amcat.tools import amcattest


class TestLexisNexis(amcattest.AmCATTestCase):
    def setUp(self):
        import os.path, json

        self.dir = os.path.join(os.path.dirname(__file__), 'test_files', 'lexisnexis')

        self.test_file = os.path.join(self.dir, 'test.txt')
        self.test_text = open(self.test_file, encoding="utf-8").read()
        self.test_file2 = os.path.join(self.dir, 'test2.txt')
        self.test_text2 = open(self.test_file2, encoding="utf-8").read()
        self.test_text3 = open(os.path.join(self.dir, 'test3.txt'), encoding="utf-8").read()

        self.test_body_sols = json.load(open(os.path.join(self.dir, 'test_body_sols.json')))
        self.test_header_sols = json.load(open(os.path.join(self.dir, 'test_header_sols.json')))

    def test_kop_as_headline(self):
        # Some lexis nexis files contain "KOP: " instaed of "HEADLINE: "
        header, body = split_header(self.test_text3)
        article = parse_article(next(split_body(body)))
        self.assertEqual("Gretta Duisenberg oprichtster van Palestina-groep", article['title'])

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

    def test_get_fields(self):
        fields = list(LexisNexis.get_fields(open(self.test_file, 'rb'), "utf-8"))
        fields = {f.label for f in fields}
        known_fields = {"title", "text", "date", "section"}
        self.assertEqual(known_fields & fields, known_fields)

    def test_parse_article(self):
        splitted = self.split()
        texts = split_body(splitted[1])
        #texts = [list(texts)[24]]; self.test_body_sols = [self.test_body_sols[23]]
        arts = []
        for t in texts:
            art = parse_article(t)
            if art:
                # Json doesn't do dates
                art['date'] = str(art['date'])
                arts.append(art)

        # Tests..
        self.assertEquals(len(arts), len(self.test_body_sols))

        for i, (found, actual) in enumerate(zip(arts, self.test_body_sols)):
            akeys = sorted(actual.keys())
            fkeys = sorted(found.keys())
            if found != actual:  # 'debug mode'
                print("Article", i, actual.get('title'))
                print("Found keys:", fkeys)
                print("Actual keys:", akeys)
                for key in sorted(set(fkeys) | set(akeys)):
                    f = found.get(key)
                    a = actual.get(key)
                    if f != a:
                        print("Key:", key, " found:", repr(f), " actual:", repr(a))
            self.assertEqual(fkeys, akeys)
            self.assertEquals(found, actual)


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
    def test_upload(self):
        """Test uploading with file map works and provenance is set correctly"""
        import os.path
        from django.core.files import File

        #fields = list(LexisNexis.get_fields(open(self.test_file, 'rb'), "utf-8"))
        fields = ["date", "title", "length_num" ,"text", "section" ,"medium"]
        field_map = {f: dict(type='field', value=f) for f in fields}
        form = dict(project=amcattest.create_test_project().id,
                    encoding="UTF-8",
                    field_map=json.dumps(field_map))

        form["articleset_name"] = "test set lexisnexis"
        aset = LexisNexis(file=File(open(self.test_file, 'rb')), **form).run()

        # form["file"] = File(open(self.test_file)),
        # aset = LexisNexis(**form).run()

        articleset = ArticleSet.objects.get(pk=aset.id)
        arts = articleset.articles.all()

        self.assertEqual(len(arts), len(self.test_body_sols))
        self.assertIn("LexisNexis query: '(((Japan OR Fukushima)", articleset.provenance)

        a = self.test_body_sols[1]
        b = articleset.articles.get(title=a['title'])

        self.assertEqual(a['text'], b.text)
        self.assertEqual(a['date'], str(b.date))
        self.assertEqual(a['length_num'], b.properties['length_num'])
        self.assertEqual(a['medium'], b.properties['medium'])

        aset = LexisNexis(file=File(open(self.test_file2, 'rb')), **form).run()
        articleset = ArticleSet.objects.get(pk=aset.id)

        # no query so provenance is the 'standard' message
        self.assertTrue(articleset.provenance.endswith("test2.txt' using LexisNexis"))
