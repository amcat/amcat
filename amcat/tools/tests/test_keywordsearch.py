from amcat.models import Language, Code
from amcat.tools import amcattest
from amcat.tools.amcattest import create_test_codebook
from amcat.tools.keywordsearch import SearchQuery, resolve_queries
from amcat.tools import djangotoolkit
from amcat.tools.toolkit import strip_accents


class TestKeywordSearch(amcattest.AmCATTestCase):
    def test_get_label_delimiter(self):
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "a"), "a")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "ab"), "a")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "ba"), "b")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "d"), None)



class TestSearchQuery(amcattest.AmCATTestCase):

    def setUp(self):
        self.codes = [
            # (label, value, parent)
            ("root", "root r", None),
            ("code1", "Code One", "root"),
            (u'\u5728\u8377\u5170\u98ce\u8f66', u'\xda\xd1\xcd\xa2\xd3\xd0\xc9 \xde\xc9X\xde', "root"),
            ("codes", "Code Collection", "root"),
            ("one", "eins OR een", "codes"),
            ("two", "zwei AND deux OR twee", "codes"),
            ("three", "drei OR drie AND trois", "two")
        ]
        self.l_lang = djangotoolkit.get_or_create(Language, label='l_lang')
        self.r_lang = djangotoolkit.get_or_create(Language, label='r_lang')
        self.codebook = self._get_test_codebook(self.codes, self.l_lang, self.r_lang)

    def test_from_string(self):
        label = u'\u5728\u8377\u5170\u98ce\u8f66'
        query_text = u'\xda\xd1\xcd\xa2\xd3\xd0\xc9 \xde\xc9X\xde'
        query = SearchQuery.from_string(u'{}#{}'.format(label, query_text))
        self.assertEqual(query.label, strip_accents(label))
        self.assertEqual(query.query, strip_accents(query_text))

    def test_resolve_queries(self):
        queries = {
            SearchQuery(u"<{}>".format(label)): result for label, result, _ in self.codes
        }

        for query, expected_result in queries.items():
            result_query = list(resolve_queries([query], self.codebook, self.l_lang, self.r_lang))[0].query
            self.assertEqual(result_query, u"({})".format(expected_result))

    def test_resolve_queries_recursive(self):
        query = SearchQuery("<root+>")

        expected_results = set(word for code in self.codes for word in code[1].split(" OR "))

        result_query = list(resolve_queries([query], self.codebook, self.l_lang, self.r_lang))[0].query
        query_words = set(result_query[1:-1].split(" OR "))
        self.assertSetEqual(query_words, expected_results)

    def _get_test_codebook(self, codes, l_lang, r_lang):
        codebook = create_test_codebook()
        code_dict = {}
        for l_label, r_label, parent_label in codes:
            parent = code_dict[parent_label] if parent_label else None
            code = codebook.create_code(label=l_label, language=l_lang, parent=parent)
            code.code.add_label(language=r_lang, label=r_label)
            code_dict[l_label] = code
        return codebook