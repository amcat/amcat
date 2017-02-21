import os.path
from amcat.scripts.article_upload.plugins.bzk_eml import BZKEML
from amcat.tools import amcattest


class TestBZKEML(amcattest.AmCATTestCase):
    def setUp(self):
        from django.core.files import File
        import os.path

        self.dir = os.path.join(os.path.dirname(__file__), 'test_files', 'bzk')
        self.bzk = BZKEML(project=amcattest.create_test_project().id,
                          file=File(open(os.path.join(self.dir, 'test.html'))),
                          articleset=amcattest.create_test_set().id)
        self.result = self.bzk.run()

    def todo_test_scrape_unit(self):
        self.assertTrue(self.result)

    def todo_test_scrape_file(self):
        #props to check for:
        # headline, text, section, medium, date
        must_props = ('headline', 'text', 'medium', 'date', 'section')
        must_props = [[getattr(a, prop) for a in self.result] for prop in must_props]

        for proplist in must_props:
            self.assertTrue(all(proplist))
