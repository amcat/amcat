from django.utils import unittest
from django.conf import settings

from amcat.scripts.article_upload import lexisnexis

import os
import chardet
import json

class TestLexisNexis(unittest.TestCase):
    def setUp(self):
        dir = os.path.join(os.path.dirname(__file__), 'test_files', 'lexisnexis')

        self.test_text = open(os.path.join(dir, 'test.txt')).read().decode('utf-8')
        self.test_body_sols = json.load(open(os.path.join(dir, 'test_body_sols.json')))
        self.test_header_sols = json.load(open(os.path.join(dir, 'test_header_sols.json')))

        self.parser = lexisnexis.LexisNexis()

    def split(self):
        return self.parser.split_header(self.test_text)

    def test_split_header(self):
        splitted = self.split()

        self.assertEquals(len(splitted[0]), 438)

    def test_split_body(self):
        splitted = self.split()

        self.assertEquals(len(list(self.parser.split_body(splitted[1]))), 4)

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

        json.dump(arts, open('test.json', 'w'), indent=2)

        # Tests..
        self.assertEquals(len(arts), len(self.test_body_sols))

        for i, art in enumerate(self.test_body_sols):
            self.assertEquals(art, arts[i])

    def test_articles(self):
        # Test for crashlessness
        self.parser.run(self.test_text)
            
