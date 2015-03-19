import os.path
import unittest
from amcat.models import ArticleSet
from amcat.scripts.article_upload.bzk_html import BZK
from amcat.tools import amcattest


@unittest.skip("BZK needs more test-files.")
class TestBZK(amcattest.AmCATTestCase):
    def setUp(self):
        from django.core.files import File
        import os.path

        self.dir = os.path.join(os.path.dirname(__file__), 'test_files', 'bzk')
        self.bzk = BZK(project=amcattest.create_test_project().id,
                       file=File(open(os.path.join(self.dir, 'test.html'))),
                       articlesets=[amcattest.create_test_set().id])
        self.result = ArticleSet.objects.get(id=self.bzk.run()[0]).articles.all()

    def todo_test_scrape_unit(self):
        self.assertTrue(self.result)

    def todo_test_scrape_file(self):
        must_props = ('headline', 'text', 'medium', 'date')
        must_props = [[getattr(a, prop) for a in self.result] for prop in must_props]

        for proplist in must_props:
            self.assertTrue(all(proplist))