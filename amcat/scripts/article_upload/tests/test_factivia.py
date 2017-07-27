import json
from datetime import datetime
from os import path
from django.core.files.uploadedfile import SimpleUploadedFile
from amcat.models import ArticleSet
from amcat.scripts.article_upload.plugins.factivia import Factivia
from amcat.scripts.article_upload.tests.test_upload import temporary_zipfile, create_test_upload
from amcat.tools import amcattest


class FactiviaTest(amcattest.AmCATTestCase):

    default_file = path.join(path.dirname(__file__), "test_files/factivia/factivia.htm")

    def get_file(self, filename):
        return path.join(path.dirname(__file__), "test_files/factivia", filename)

    def test_get_fields(self):
        fields = Factivia.get_fields(self.get_file("factivia.htm"), "utf-8")
        fnames = {f.label for f in fields}
        self.assertIn("date", fnames)
        self.assertIn("title", fnames)

    def get_articles(self, filename=default_file):
        project = amcattest.create_test_project()
        upload = create_test_upload(filename, project, project.owner)
        articleset = amcattest.create_test_set().id
        fields = ['date', 'page_int', 'title', 'author', 'text', 'length_int', 'medium']
        field_map = {k: {"type": "field", "value": k.split("_")[0]} for k in fields}
        form = dict(project=amcattest.create_test_project().id,
                    articleset=articleset, field_map=json.dumps(field_map), encoding='utf-8',
                    upload=upload.id)
        Factivia(**form).run()
        return ArticleSet.objects.get(pk=articleset).articles.all()

    @amcattest.use_elastic
    def test_factivia(self):
        articles = self.get_articles()

        self.assertEqual(9, len(articles))

        first_article = articles.get(title="Laut Rechtsprofessoren liegt die SVP falsch")
        self.assertEqual(datetime(2013, 11, 19), first_article.date)
        self.assertEqual("Die S\xfcdostschweiz", first_article.properties['medium'])
        self.assertEqual(475, first_article.properties['length_int'])
        self.assertEqual(14, first_article.properties['page_int'])
        self.assertEqual("Lorenz Honegger", first_article.properties['author'])

        self.assertIn("Die SVP sieht sich in ihrem Argwohn", first_article.text)
        self.assertIn("Heimatstaat von Folter oder Tod bedroht sind", first_article.text)
        self.assertIn("Ob die umstrittene Stelle aus der Initiative gestrichen wird", first_article.text)

    @amcattest.use_elastic
    def test_az01(self):
        # Just check for errorlessness
        self.get_articles(self.get_file("az01.htm"))

    @amcattest.use_elastic
    def test_so00(self):
        # Just check for errorlessness
        self.get_articles(self.get_file("SO00.htm"))

    @amcattest.use_elastic
    def test_ww04(self):
        articles = self.get_articles(self.get_file("ww04.htm"))

        article = articles.get(title="Vor dieser Stadt wird gewarnt")
        self.assertEqual(datetime(2012, 6, 28), article.date)
        self.assertEqual("Weltwoche", article.properties['medium'])
        self.assertEqual("Lucien Scherrer", article.properties['author'])

    @amcattest.use_elastic
    def test_zt04(self):
        articles = self.get_articles(self.get_file("zt04.htm"))

        article = articles.get(title="Das ganze volle Leben in der Zeitung")
        self.assertEqual(datetime(2011, 8, 10), article.date)
        self.assertEqual(569, article.properties['length_int'])
        self.assertEqual("Zofinger Tagblatt", article.properties['medium'])
        self.assertEqual(None, article.properties.get('page_int'))

    @amcattest.use_elastic
    def test_zip(self):
        files = [
            self.get_file("ww04.htm"),
            self.get_file("zt04.htm")
        ]
        with temporary_zipfile(files) as f:
            articles = self.get_articles(f)

        # test existence
        articles.get(title="Vor dieser Stadt wird gewarnt") # from ww04
        articles.get(title="Das ganze volle Leben in der Zeitung") # from zt04
