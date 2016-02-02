from __future__ import absolute_import
from __future__ import unicode_literals
from amcat.tools import amcattest
from amcat.tools.keywordsearch import SearchQuery


class TestKeywordSearch(amcattest.AmCATTestCase):
    def test_get_label_delimiter(self):
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "a"), "a")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "ab"), "a")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "ba"), "b")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "d"), None)