import os.path
from amcat.scripts.article_upload.plugins.bzk_pdf import BZKPDFScraper
from amcat.tools import amcattest


class TestBZK(amcattest.AmCATTestCase):
    def setUp(self):
        if amcattest.skip_slow_tests(): return

        from django.core.files import File
        import os.path, json
        self.dir = os.path.join(os.path.dirname(__file__), 'test_files', 'bzk')
        self.bzk = BZKPDFScraper(project = amcattest.create_test_project().id,
                       file = File(open(os.path.join(self.dir, 'test.pdf'))),
                       articleset = amcattest.create_test_set().id)
        self.result = self.bzk.run()


        def test_scrape_unit(self):
            if amcattest.skip_slow_tests(): return

            self.assertTrue(self.bzk.index)
            self.assertTrue(self.result)

        def test_getarticle(self):
            if amcattest.skip_slow_tests(): return

            #props to check for:
            # headline, text, date, pagenr, medium
            must_props = ('headline', 'text', 'medium', 'date')
            may_props = ('pagenr',)
            must_props = [[getattr(a.props, prop) for a in self.result] for prop in must_props]
            may_props = [[getattr(a.props, prop) for a in self.result] for prop in may_props]

            for proplist in must_props:
                self.assertTrue(all(proplist))
            for proplist in may_props:
                #assuming at least one of the articles has the property. if not, break.
                self.assertTrue(any(proplist))
