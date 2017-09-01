import datetime
import json
import os.path
import unittest
from amcat.models import ArticleSet
from amcat.scripts.article_upload.plugins.bzk_html import BZK
from amcat.scripts.article_upload.tests.test_upload import temporary_zipfile, create_test_upload
from amcat.tools import amcattest


def _rmcache(fn):
    cachefn = fn + "__upload_cache.json"
    if os.path.exists(cachefn):
        os.remove(cachefn)
    return fn

class TestBZK(amcattest.AmCATTestCase):
    def setUp(self):
        from django.core.files import File
        import os.path
        self.project = amcattest.create_test_project()
        self.dir = os.path.join(os.path.dirname(__file__), 'test_files', 'bzk')
        self.file_scrape1 = os.path.join(self.dir, 'test.html')
        self.file_scrape2 = os.path.join(self.dir, 'test_scrape2.html')

    def test_get_fields(self):
        upload = create_test_upload(self.file_scrape1, project=self.project)
        fields = set(f.label for f in BZK.get_fields(upload))
        self.assertIn("title", fields)
        self.assertIn("date", fields)
        self.assertIn("text", fields)

    def _create_id_field_map(self, *fields):
        """
        Creates a json formatted identity field map where each source and destination is the same.
        """
        return json.dumps({field : {"type": "field", "value": field} for field in fields})

    @amcattest.use_elastic
    def _test_parse_file(self, file, n_articles, min_article_length=20, expected_articles=()):
        """
        Tests the parsing of a file using the scrape_2 format.
        @param expected_articles    A sequence of {field: value} dicts, each with at least a 'title' field.
        """
        field_map = self._create_id_field_map("title", "text", "medium", "date")
        upload = create_test_upload(file, "utf-8", project=self.project)
        script = BZK(field_map=field_map, upload=upload.id, project=self.project.id, encoding="utf-8")
        result_set = script.run()
        self.assertIsInstance(result_set, ArticleSet)
        articles = list(result_set.articles.all())
        self.assertEqual(len(articles), n_articles)
        article_map = {a.title: a for a in articles}
        for fields in expected_articles:
            title = fields['title']
            article = article_map[title]
            self.assertGreaterEqual(len(article.text), min_article_length)
            for field, value in fields.items():
                self.assertEqual(article.get_property(field), value,
                                 "Expected value '{}' for article field '{}'".format(value, field))



    @amcattest.use_elastic
    def test_parse_file_scrape1(self):
        """
        Tests the parsing of a file using the scrape_1 format.
        """
        self._test_parse_file(self.file_scrape1, 45)

    @amcattest.use_elastic
    def test_parse_file_zipfile(self):
        """
        Tests the parsing of a zipfile using the scrape_1 and scrape_2 formats.
        """
        with temporary_zipfile([self.file_scrape1, self.file_scrape2]) as f:
            self._test_parse_file(f, 45 + 51)

    @amcattest.use_elastic
    def test_parse_file_scrape2(self):
        """
        Tests the parsing of a file using the scrape_2 format.
        """
        expected_articles = [
            {"title": "Staat schond persvrijheid Telegraaf", "date": datetime.datetime(2017, 1, 5)},
            {"title": "Neprom hekelt uitzonderingspositie energie-eisen Amsterdam en Den Haag"},
            {"title": "Opposition thrown out of Curaçao Parliament", "date": datetime.datetime(2017, 1, 4)},
            {"title": "Statia petitions against embedding public entity in Dutch Constitution",
             "date": datetime.datetime(2017, 1, 5) }
        ]
        self._test_parse_file(self.file_scrape2, 51, expected_articles=expected_articles)


    @unittest.skip("No test files for format 3")
    @amcattest.use_elastic
    def test_parse_file_scrape3(self):
        """
        Tests the parsing of a file using the scrape_3 format.
        """
        pass

