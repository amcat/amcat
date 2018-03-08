from amcat.models import Language, Code, ArticleSet, Article
from amcat.scripts.forms import SelectionForm
from amcat.tools import amcattest
from amcat.tools.amcattest import create_test_codebook, create_test_set, create_test_article, use_elastic
from amcat.tools.keywordsearch import SearchQuery, resolve_queries, SelectionSearch
from amcat.tools import djangotoolkit
from amcat.tools.toolkit import strip_accents


class TestKeywordSearch(amcattest.AmCATTestCase):
    def test_get_label_delimiter(self):
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "a"), "a")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "ab"), "a")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "ba"), "b")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "d"), None)


class SelectionSearchTestCase(amcattest.AmCATTestCase):
    articles = None
    queries = None

    def _setUp(self):
        """ _setUp instead of setUp for @use_elastic compatibility. """
        self.articleset = create_test_set()
        self.articles = [create_test_article(articleset=self.articleset, **article) for article in type(self).articles]
        self.article_ids = [article.id for article in self.articles]
        self.articleset.refresh_index()

    @use_elastic
    def _run_query(self, form_data, expected_indices=None, expected_count=None):
        self._setUp()
        sets = ArticleSet.objects.filter(pk=self.articleset.pk)
        form = SelectionForm(articlesets=sets, project=self.articleset.project, data=form_data)
        form.full_clean()
        self.assertFalse(form.errors, "Form contains errors")

        search = SelectionSearch(form)
        if expected_indices:
            article_ids = search.get_article_ids()
            articles = Article.objects.filter(id__in=article_ids)
            expected = [self.articles[i] for i in expected_indices]
            self.assertSetEqual(set(articles), set(expected))

        if expected_count:
            self.assertEqual(search.get_count(), expected_count)

class TestSelectionSearchQuery(SelectionSearchTestCase):
    articles = [
        {"title": "Foo", "text": "bar", "date": "2015-05-05"},
        {"title": "Julius Caesar said:", "text": "alea iacta est", "date": "0040-01-10"},
        {"title": "Also phrased as", "text": "iacta alea est", "date": "0040-01-10"}
    ]

    def test_empty_query(self):
        self._run_query({}, [0, 1, 2])

    def test_simple_query(self):
        self._run_query({"query": "foo"}, [0])
        self._run_query({"query": "est"}, [1, 2])

    def test_bool_query(self):
        self._run_query({"query": "est OR foo"}, [0, 1, 2])
        self._run_query({"query": "est AND foo"}, [])
        self._run_query({"query": "est AND said"}, [1])


class TestSelectionSearchDateRange(SelectionSearchTestCase):
    articles = [
        {"title": "Foo", "text": "bar", "date": "2015-05-05"},
        {"title": "Julius Caesar said:", "text": "alea iacta est", "date": "0040-01-10"},
        {"title": "Also phrased as", "text": "iacta alea est", "date": "0040-01-10"},
        {"title": "The origin of species", "text": "When on board H.M.S. Beagle, as naturalist...",
         "date": "1859-11-24"}
    ]

    def test_after(self):
        self._run_query({"start_date": "1000-10-10", "datetype": "after"}, [0, 3])

    def test_before(self):
        self._run_query({"end_date": "1000-10-10", "datetype": "before"}, [1, 2])

    def test_between(self):
        self._run_query({"start_date": "1000-10-10", "end_date": "1999-09-09", "datetype": "between"}, [3])

    def test_relative(self):
        self._run_query({"relative_date": "-15768000000", "datetype": "relative"}, [0, 3])


class TestSelectionSearchFilters(SelectionSearchTestCase):
    articles = [
        {"title": "Foo", "text": "bar", "date": "2015-05-05", "properties": {"author": "Plutarch"}},
        {"title": "Julius Caesar said:", "text": "alea iacta est", "date": "0049-01-10",
         "properties": {"author": "Suetonius"}},
        {"title": "Also phrased as", "text": "iacta alea est", "date": "0049-01-10",
         "properties": {"author": "Plutarch"}},
        {"title": "Different author is different", "text": "foo", "date": "0049-01-10",
         "properties": {"author": "Plutarch et. al"}},
        {"title": "Book about things",
         "text": "This book is about things plato probably would've had something to say about things. The end.",
         "date": "2004-04-04",
         "properties": {"edition_int": 1}},
        {"title": "Book about things",
         "text": "This book is about things. Plato probably would've had something to say about things. The end.",
         "date": "2004-04-04",
         "properties": {"edition_int": 3}},
        {"title": "Book about things",
         "text": "This book is about things. Plato probably would've had something to say about things. The end.",
         "date": "2004-04-04",
         "properties": {"edition_int": 3, "owner": "Socrates"}}
    ]

    def test_filter(self):
        self._run_query({"filters": '{"author":"Plutarch"}'}, [0, 2])
        self._run_query({"filters": '{"edition_int": 3}'}, [5, 6])

    def test_multiple_filters(self):
        self._run_query({"filters": '{"edition_int": 3, "owner": "Socrates"}'}, [6])


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