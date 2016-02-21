import os.path
import unittest
import zipfile
from tempfile import NamedTemporaryFile

from django.core.files import File

from amcat.models import Article, ArticleSet
from amcat.scripts.article_upload.text import Text
from amcat.tools import amcattest


class TestUploadText(amcattest.AmCATTestCase):
    @amcattest.use_elastic
    @unittest.skip("Controller is a complete mess")
    def test_article(self):
        from django.core.files import File

        base = dict(project=amcattest.create_test_project().id,
                    articleset=amcattest.create_test_set().id,
                    medium=amcattest.create_test_medium().id)
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile(prefix=u"1999-12-31_\u0409\u0429\u0449\u04c3", suffix=".txt") as f:
            text = u'H. C. Andersens for\xe6ldre tilh\xf8rte samfundets laveste lag.'
            f.write(text.encode('utf-8'))
            f.flush()

            dn, fn = os.path.split(f.name)
            fn, ext = os.path.splitext(fn)
            a, = Text(dict(date='2010-01-01', headline='simple testxxx',
                           file=File(open(f.name)), encoding=0, **base)).run()
            a = Article.objects.get(pk=a.id)
            self.assertEqual(a.headline, 'simple test')
            self.assertEqual(a.date.isoformat()[:10], '2010-01-01')
            self.assertEqual(a.text, text)


            # test autodect headline from filename
            a, = Text(dict(date='2010-01-01',
                           file=File(open(f.name)), encoding=0, **base)).run()
            a = Article.objects.get(pk=a.id)
            self.assertEqual(a.headline, fn)
            self.assertEqual(a.date.isoformat()[:10], '2010-01-01')
            self.assertEqual(a.text, text)
            self.assertEqual(a.section, dn)

            # test autodect date and headline from filename
            a, = Text(dict(file=File(open(f.name)), encoding=0, **base)).run()
            a = Article.objects.get(pk=a.id)
            self.assertEqual(a.headline, fn.replace("1999-12-31_", ""))
            self.assertEqual(a.date.isoformat()[:10], '1999-12-31')
            self.assertEqual(a.text, text)

    @amcattest.use_elastic
    def test_zip(self):
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