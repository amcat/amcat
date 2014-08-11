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

from os import path
from datetime import datetime
from lxml import html

from django.core.files.uploadedfile import SimpleUploadedFile
from amcat.models import Medium, Article, ArticleSet
from amcat.scripts.article_upload.upload import UploadScript

from amcat.tools import amcattest
from amcat.tools import toolkit

META = ["headline", "length", "date", "medium", None, "pagenr"]

PROCESSORS = {
    "length": lambda l: int(l.rstrip("words")),
    "date": toolkit.read_date,
    "medium": Medium.get_or_create,
    "pagenr": lambda p: int(p) if p.strip().isdigit() else None
}


class Factivia(UploadScript):
    def split_file(self, file):
        # Parses HTML file (bytes) to a more convienient lxml representation
        document = html.fromstring(file.read())

        # Selects all elements with class=article
        return document.cssselect(".article")

    def _scrape_unit(self, document):
        article = Article()
        metadata = list(META)

        # We select all 'div' elements directly under '.article'
        divs = document.cssselect("* > div")

        # Check for author field. If present: remove from metadata
        # fields list
        try:
            author_field = document.cssselect(".author")[0]
        except IndexError:
            pass
        else:
            article.author = author_field.text_content().lstrip("Von").strip()
            divs.remove(author_field)

        # Strip everything before headline
        headline_field = document.cssselect("b.deHeadline")[0].getparent()
        divs = divs[divs.index(headline_field):]

        # Parse metadata. Loop through each 'div' within an article, along with
        # its field name according to META (thus based on its position)
        for field_name, element in zip(metadata, divs):
            if field_name is None:
                continue

            processor = PROCESSORS.get(field_name, lambda x: x)
            text_content = element.text_content().strip()
            setattr(article, field_name, processor(text_content))

        # Fetch text, which is
        paragraphs = [p.text_content() for p in document.cssselect("p")]
        article.text = ("\n\n".join(paragraphs)).strip()

        # We must return a iterable, so we return a one-tuple
        return (article,)


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
