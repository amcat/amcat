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
from amcat.tools.caching import cached

META = [
    "headline", "author", "length", "date",
    "medium", None, "pagenr"
]

PROCESSORS = {
    "author": lambda a: a.lstrip("Von "),
    "length": lambda l: int(l.rstrip("words")),
    "date": toolkit.read_date,
    "medium": Medium.get_or_create,
    "pagenr": int
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

        # Some articles do not mention an author, so we need to remove it from
        # the list of metadata
        author_field = divs[META.index("author")]
        if "Von" not in author_field.text_content():
            metadata.remove("author")

        # Parse metadata. Loop through each 'div' within an article, along with
        # its field name according to META (thus based on its position)
        for field_name, element in zip(metadata, document.cssselect("* > div")):
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
    @property
    def scraper(self):
        test_file = path.join(path.dirname(__file__), "test_files/factivia.htm")

        return Factivia(options={
            'project': amcattest.create_test_project().id,
            'articlesets': [amcattest.create_test_set().id],
            'file': SimpleUploadedFile.from_dict({
                "filename": "factivia.htm",
                "content": open(test_file).read(),
                "content_type": "text/html"
            })
        })

    @property
    def articles(self):
        return self.get_articles()

    @cached
    def get_articles(self):
        return ArticleSet.objects.get(id__in=self.scraper.run()).articles.all()

    ### TESTS ###
    @amcattest.use_elastic
    def test_scraping(self):
        self.assertEqual(9, len(self.articles))

        first_article = self.articles.get(headline="Laut Rechtsprofessoren liegt die SVP falsch")
        self.assertEqual(475, first_article.length)
        self.assertEqual(datetime(2013, 11, 19), first_article.date)
        self.assertEqual("Die S\xfcdostschweiz", first_article.medium.name)
        self.assertEqual(14, first_article.pagenr)

        self.assertIn("Die SVP sieht sich in ihrem Argwohn", first_article.text)
        self.assertIn("Heimatstaat von Folter oder Tod bedroht sind", first_article.text)
        self.assertIn("Ob die umstrittene Stelle aus der Initiative gestrichen wird", first_article.text)
