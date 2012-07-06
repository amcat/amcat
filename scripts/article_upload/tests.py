import os
import json
import datetime

from django.utils import unittest
from django.conf import settings

from amcat.scripts.article_upload import lexisnexis, mediargus
from amcat.models.medium import Medium
from amcat.models.language import Language
from amcat.models.project import Project
from amcat.models.user import Affiliation, User
from amcat.models.authorisation import Role
from amcat.tools import amcattest

class TestLexisNexis(unittest.TestCase):
    def setUp(self):
        dir = os.path.join(os.path.dirname(__file__), 'test_files', 'lexisnexis')

        self.test_text = open(os.path.join(dir, 'test.txt')).read().decode('utf-8')
        self.test_body_sols = json.load(open(os.path.join(dir, 'test_body_sols.json')))
        self.test_header_sols = json.load(open(os.path.join(dir, 'test_header_sols.json')))

        self.parser = lexisnexis.LexisNexis(project=amcattest.create_test_project().id)

    def split(self):
        return self.parser.split_header(self.test_text)

    def test_split_header(self):
        splitted = self.split()

        self.assertEquals(len(splitted[0]), 438)

    def test_split_body(self):
        splitted = self.split()

        self.assertEquals(len(list(self.parser.split_body(splitted[1]))), 5)

    def test_parse_header(self):
        splitted = self.split()

        self.maxDiff = None
        meta = self.parser.parse_header(splitted[0])
        self.assertEquals(meta, self.test_header_sols)

    def test_parse_article(self):
        splitted = self.split()
        arts = self.parser.split_body(splitted[1])

        # Json doesn't do dates
        arts = [list(self.parser.parse_article(a)) for a in arts]
        for art in arts: art[3] = str(art[3])

        # Tests..
        self.assertEquals(len(arts), 5)

        for i, art in enumerate(self.test_body_sols):
            self.assertEquals(art, arts[i])

    def _create_medium(self, source):
        try:
            Medium.objects.get(name__iexact=source)
        except Medium.DoesNotExist:
            l = Language.objects.get(id=1)
            Medium(name=source, abbrev=source[0:5], circulation=1, language=l).save()


    def test_meta(self):

        a = list(self.parser.split_body(self.split()[1]))[0]
        meta = self.parser.parse_article(a)[-1]
        self.assertEqual(meta.pop('length').split()[0], "306")

    def test_body_to_article(self):
        articles = self.parser.split_body(self.split()[1])
        articles = [self.parser.parse_article(a) for a in articles]

        # Only testing the first article. If this contains correct
        # data, we assume the implementation is correct. However,
        # we do test the remaining articles with full_clean().

        art = self.parser.body_to_article(*articles[0])
        self.assertEquals(art.length, 306)
        self.assertEquals(art.headline, "This is a headline")
        self.assertEquals(art.byline, "with a byline. The article contains unicode characters.")
        self.assertEquals(art.text, articles[0][2])
        self.assertEquals(art.date, datetime.datetime(2011, 8, 31))
        self.assertEquals(art.medium.name, u"B\u00f6rsen-Zeitung")
        self.assertEquals(art.author, "MF Tokio")
        self.assertEquals(eval(art.metastring), {u'update': u'2. September 2011',
                                                 u'language': u'GERMAN; DEUTSCH',
                                                 u'publication-type': u'Zeitung'})

        # Setup environment
        dp = amcattest.create_test_project()

        # Test remaining articles
        for art in articles[1:]:
            self._create_medium(art[4])

            p = self.parser.body_to_article(*art)
            p.project = dp
            p.full_clean()




class TestMediargus(unittest.TestCase):

    def setUp(self):
        self.test_file = os.path.join(os.path.dirname(__file__), 'test_files', 'mediargus.txt')
        self.test_text = open(self.test_file).read().decode('latin-1')

    def test_split(self):
        articles = mediargus.Mediargus(project=amcattest.create_test_project().id).split_text(self.test_text)
        self.assertEqual(len(articles), 100)
        for article in articles:
            self.assertEqual(len(article), 2)

    def test_parse(self):
        m = mediargus.Mediargus(project=amcattest.create_test_project().id)
        articles = m.split_text(self.test_text)
        a = m.parse_document(articles[99])
        self.assertEqual(a.headline, 'Maatschappijkritiek en actualiteit als inspiratie')
