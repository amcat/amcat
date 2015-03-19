from __future__ import unicode_literals, print_function

from datetime import datetime
from os import path
from django.core.files.uploadedfile import SimpleUploadedFile
from amcat.models import ArticleSet
from amcat.scripts.article_upload.factivia import Factivia
from amcat.tools import amcattest


class FactiviaTest(amcattest.AmCATTestCase):
    ### SCRAPE LOGIC ###
    def get_scraper(self, filename):
        test_file = path.join(path.dirname(__file__), "test_files/factivia", filename)

        return Factivia(options={
            'project': amcattest.create_test_project().id,
            'articlesets': [amcattest.create_test_set().id],
            'file': SimpleUploadedFile.from_dict({
                "filename": filename,
                "content": open(test_file).read(),
                "content_type": "text/html"
            })
        })

    def get_articles(self, filename="factivia.htm"):
        articlesets = self.get_scraper(filename).run()
        return ArticleSet.objects.get(id__in=articlesets).articles.all()

    ### TESTS ###
    @amcattest.use_elastic
    def test_factivia(self):
        articles = self.get_articles()

        self.assertEqual(9, len(articles))

        first_article = articles.get(headline="Laut Rechtsprofessoren liegt die SVP falsch")
        self.assertEqual(475, first_article.length)
        self.assertEqual(datetime(2013, 11, 19), first_article.date)
        self.assertEqual("Die S\xfcdostschweiz", first_article.medium.name)
        self.assertEqual(14, first_article.pagenr)
        self.assertEqual("Lorenz Honegger", first_article.author)

        self.assertIn("Die SVP sieht sich in ihrem Argwohn", first_article.text)
        self.assertIn("Heimatstaat von Folter oder Tod bedroht sind", first_article.text)
        self.assertIn("Ob die umstrittene Stelle aus der Initiative gestrichen wird", first_article.text)

    @amcattest.use_elastic
    def test_az01(self):
        # Just check for errorlessness
        self.get_articles("az01.htm")

    @amcattest.use_elastic
    def test_so00(self):
        # Just check for errorlessness
        self.get_articles("SO00.htm")

    @amcattest.use_elastic
    def test_ww04(self):
        articles = self.get_articles("ww04.htm")

        article = articles.get(headline="Vor dieser Stadt wird gewarnt")
        self.assertEqual(2068, article.length)
        self.assertEqual(datetime(2012, 6, 28), article.date)
        self.assertEqual("Weltwoche", article.medium.name)
        self.assertEqual(None, article.pagenr)
        self.assertEqual("Lucien Scherrer", article.author)

    @amcattest.use_elastic
    def test_zt04(self):
        articles = self.get_articles("zt04.htm")

        article = articles.get(headline="Das ganze volle Leben in der Zeitung")
        self.assertEqual(569, article.length)
        self.assertEqual(datetime(2011, 8, 10), article.date)
        self.assertEqual("Zofinger Tagblatt", article.medium.name)
        self.assertEqual(None, article.pagenr)