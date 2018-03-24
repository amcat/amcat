import json
import os

from amcat.scripts.article_upload.plugins.apa_prof import APA
from amcat.scripts.article_upload.tests.test_upload import create_test_upload
from amcat.tools import amcattest
from amcat.tools.amcattest import create_test_project, create_test_set


class TestApaProf(amcattest.AmCATTestCase):
    def setUp(self):
        self.project = create_test_project()

    def get_form(self, file, **kwargs):
        project = self.project
        articleset = create_test_set(project=project)
        upload = create_test_upload(file, project=project)
        field_map = {f.label: dict(type="field", value=f.suggested_destination) for f in APA.get_fields(upload)}
        form = APA.form_class(
            data=dict(project=project.id, articleset=articleset.id, encoding="utf-8", upload=upload.id,
                      field_map=json.dumps(field_map), **kwargs))
        self.assertTrue(form.is_valid(), form.errors)
        return form

    def test_parse_document(self):
        f = os.path.join(os.path.dirname(__file__), "test_files/apa/online.rtf")
        form = self.get_form(f)
        file = list(form.cleaned_data['upload'].get_files())[0]
        arts = list(APA(form).parse_file(file, None))
        self.assertEqual(len(arts), 38)

    def test_parse_onlinemanager(self):
        f = os.path.join(os.path.dirname(__file__), "test_files/apa/onlinemanager.rtf")
        form = self.get_form(f)
        file = list(form.cleaned_data['upload'].get_files())[0]
        arts = list(APA(form).parse_file(file, None))
        self.assertEqual(len(arts), 20)

        headlines = [a.title for a in arts]
        self.assertIn("Eine Urne als Glücksbringer des Hauses der Geschichte", headlines)