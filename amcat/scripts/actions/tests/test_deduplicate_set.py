import uuid
import datetime
from collections import Hashable

from amcat.models import ArticleSet
from amcat.scripts.actions.deduplicate_set import DeduplicateSet
from amcat.tools import amcattest
from amcat.tools.amcates import ES


class TestDeduplicateSet(amcattest.AmCATTestCase):
    def _set_up(self):
        # must be called manually.

        self.project = amcattest.create_test_project()
        now = datetime.datetime.now()
        articles = [
            {"title": "one", "text": "two", "date": now, "properties": {"field": "three", "unique_id": "1"}},
            {"title": "one", "text": "two", "date": now, "properties": {"field": "three", "unique_id": "2"}},
            {"title": "title", "text": "text", "date": now, "properties": {"unique_id": "3"}},
            {"title": "title", "text": "text", "date": now, "properties": {"unique_id": "4"}},
            {"title": "title", "text": "text", "date": now, "properties": {"unique_id": "5"}},
        ]
        self.test_set = amcattest.create_test_set(project=self.project)
        self.articles = [amcattest.create_test_article(articleset=self.test_set, **fields) for fields in articles]

        self.test_set.add(*self.articles)

        self.test_set.refresh_index(True)
        self.base_options = {
            "articleset": self.test_set.id,
            "ignore_fields": set(),
            "save_duplicates_to": None,
            "dry_run": False,
        }
        ES().refresh()

    @amcattest.use_elastic
    def test_deduplicate(self):
        self._set_up()
        options = dict(self.base_options, ignore_fields=("unique_id",))
        ds = DeduplicateSet(options=options)
        n, _ = ds.run()
        ES().refresh()
        self.assertEqual(n, 3, "Unexpected number of duplicates.")
        self.assertEqual(self.test_set.get_count(), 2, "Unexpected number of articles in the articleset")
        self.assertSetEqual(
            {x.title for x in self.test_set.articles.all()},
            {self.articles[0].title, self.articles[2].title},
            "Unexpected articles found in resulting set"
        )

    @amcattest.use_elastic
    def test_dry_run(self):
        self._set_up()
        options = dict(self.base_options, ignore_fields=("unique_id",), dry_run=True)
        ds = DeduplicateSet(options=options)
        n, _ = ds.run()
        ES().refresh()
        self.assertEqual(n, 3, "Unexpected number of duplicates.")
        self.assertEqual(self.test_set.get_count(), 5, "Articles should not be removed in dry run.")

    @amcattest.use_elastic
    def test_save_duplicates(self):
        self._set_up()
        duplicate_set_name = uuid.uuid4().hex
        options = dict(self.base_options, ignore_fields=("unique_id",), save_duplicates_to=duplicate_set_name)
        ds = DeduplicateSet(options=options)
        n, _ = ds.run()
        ES().refresh()
        duplicate_set = ArticleSet.objects.get(name=duplicate_set_name)
        self.assertEqual(n, 3, "Unexpected number of duplicates.")
        self.assertEqual(self.test_set.get_count(), 2, "Unexpected number of articles in the original set")
        self.assertEqual(duplicate_set.get_count(), 3, "Unexpected number of articles in the duplicates set")

    @amcattest.use_elastic
    def test_hash_articles(self):
        self._set_up()
        hashes = dict(DeduplicateSet.hash_articles(self.test_set, ignore_fields=("unique_id",)))
        self.assertEqual(hashes[self.articles[0].id], hashes[self.articles[1].id])
        self.assertEqual(hashes[self.articles[2].id], hashes[self.articles[3].id])
        self.assertNotEqual(hashes[self.articles[0].id], hashes[self.articles[2].id])

    @amcattest.use_elastic
    def test_hash_property_fields(self):
        self._set_up()
        hashes = dict(DeduplicateSet.hash_articles(self.test_set, ignore_fields=("title", "text", "unique_id")))
        self.assertEqual(hashes[self.articles[0].id], hashes[self.articles[1].id])
        self.assertEqual(hashes[self.articles[2].id], hashes[self.articles[3].id])
        self.assertNotEqual(hashes[self.articles[0].id], hashes[self.articles[2].id])

        hashes = dict(DeduplicateSet.hash_articles(self.test_set, ignore_fields=("title", "text", "field")))
        unique_hashes = set(hashes[self.articles[i].id] for i in range(5))
        self.assertEqual(len(unique_hashes), 5)

    def _get_es_like_articles(self, articles):
        """
        @param articles: A list of {field: value} dicts
        @return: A list of ES-like article dicts
        """
        return [
            {
                'fields': {k: [v] for k, v in article.items()},
                '_index': 'amcat',
                '_type': 'article',
                '_id': i,
                '_score': 0.0
            }
            for i, article in enumerate(articles)]
