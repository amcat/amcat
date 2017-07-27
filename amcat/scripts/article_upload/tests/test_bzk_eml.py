import os.path
from amcat.scripts.article_upload.plugins.bzk_eml import BZKEML
from amcat.scripts.article_upload.tests.test_upload import create_test_upload
from amcat.tools import amcattest


class TestBZKEML(amcattest.AmCATTestCase):
    def setUp(self):
        from django.core.files import File
        import os.path
        project = amcattest.create_test_project()
        user = project.owner
        file = File(open(os.path.join(self.dir, 'test.html')))
        upload = create_test_upload(file, project, user)
        self.dir = os.path.join(os.path.dirname(__file__), 'test_files', 'bzk')
        self.bzk = BZKEML(project=project.id,
                          upload=upload.id,
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
