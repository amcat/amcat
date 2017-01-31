import json
import os.path
import zipfile
from tempfile import NamedTemporaryFile

from django.core.files import File

from amcat.models import ArticleSet
from amcat.scripts.article_upload.text import Text
from amcat.tools import amcattest


def _test(field_map, text="test_text", fn_prefix=None):
    """Run Text uploader with given argumens and return 'uploaded' articles"""
    with NamedTemporaryFile(prefix=fn_prefix, suffix=".txt") as f:
        f.write(text.encode('utf-8'))
        f.flush()
        aset = amcattest.create_test_set().id
        form = dict(project=amcattest.create_test_project().id,
                    filename=File(open(f.name)),
                    encoding='UTF-8',
                    field_map=json.dumps(field_map),
                    articleset=aset)
        Text(**form).run()
        fn = os.path.splitext(os.path.basename(f.name))[0]
    return fn, ArticleSet.objects.get(pk=aset).articles.all()


class TestUploadText(amcattest.AmCATTestCase):
    @amcattest.use_elastic
    def test_article(self):
        field_map = dict(title={"type": "field", "value": "filename"},
                         date={"type": "literal", "value": "2016-01-01"},
                         text={"type": "field", "value": "text"},
                         custom={"type": "literal", "value": "test"})
        fn, (a,) = _test(field_map, text="test")
        self.assertEqual(a.title, fn)
        self.assertEqual(a.date.isoformat()[:10], '2016-01-01')
        self.assertEqual(a.text, "test")
        self.assertEqual(dict(a.properties), {"custom": "test"})

    @amcattest.use_elastic
    def test_fieldname_parts(self):
        text = u'H. C. Andersens for\xe6ldre tilh\xf8rte samfundets laveste lag.'
        date = "1999-12-31"
        name = "\u0409\u0429\u0449\u04c3"

        field_map = dict(title={"type": "field", "value": "filename-2"},
                         date={"type": "field", "value": "filename-1"},
                         text={"type": "field", "value": "text"})
        _, (a,) = _test(field_map, text, fn_prefix="{date}_{name}_".format(**locals()))
        self.assertEqual(a.title, name)
        self.assertEqual(a.date.isoformat()[:10], date)
        self.assertEqual(a.text, text)


    @amcattest.use_elastic
    def todo_test_zip(self):
        base = dict(project=amcattest.create_test_project().id,
                    articlesets=[amcattest.create_test_set().id],
                    medium=amcattest.create_test_medium().id)

        with NamedTemporaryFile(prefix=u"upload_test", suffix=".zip") as f:
            with zipfile.ZipFile(f, "w") as zf:
                zf.writestr("headline1.txt", "TEXT1")
                zf.writestr("x/headline2.txt", "TEXT2")
            f.flush()

            s = Text(file=File(f), date='2010-01-01', **base)
            arts = list(ArticleSet.objects.get(id=s.run()[0]).articles.all())
            self.assertEqual({a.headline for a in arts}, {"headline1", "headline2"})
            self.assertEqual({a.section for a in arts}, {'', "x"})
            self.assertEqual({a.text for a in arts}, {"TEXT1", "TEXT2"})