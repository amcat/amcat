import csv
import io

from amcat.tools import amcattest
from amcat.scripts.actions.import_codebook import ImportCodebook

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

def _run_test(bytes, **options):
    if 'project' not in options: options['project'] = amcattest.create_test_project().id
    if 'codebook_name' not in options: options['codebook_name'] = 'test'
    if 'default_language' not in options: options['default_language'] = 1
    from tempfile import NamedTemporaryFile
    from django.core.files import File

    with NamedTemporaryFile(suffix=".txt") as f:
        f.write(bytes)
        f.flush()

        return ImportCodebook(dict(file=File(open(f.name, "rb")), **options)).run()


def _csv_bytes(rows, encoding="utf-8", **kargs):
    out = io.StringIO()
    w = csv.writer(out, **kargs)
    for row in rows:
        w.writerow(row)
    return out.getvalue().encode(encoding)


class TestImportCodebook(amcattest.AmCATTestCase):
    def _standardize_cb(self, codebook, **kargs):
        """return a dense hierarchy serialiseation for easier comparisons"""
        return ";".join(sorted(set("{0}:{1}".format(*cp)
                                   for cp in codebook.get_hierarchy(**kargs))))

    def test_import(self):
        c = [("Code-1", "Code-2", "Code-3"),
             ("root", None, None),
             (None, "sub1", None),
             (None, None, u"sub1a")]
        b = _csv_bytes(c)
        self.assertEqual(self._standardize_cb(_run_test(b)), u"root:None;sub1:root;sub1a:sub1")

    def test_unicode(self):
        test1, test2 = u'code_\xe9', u'c\xd8de'
        c = [("c1","label - test"),
             (test1, test2)]
        for encoding in ('UTF-8', 'Latin-1'):
            b = _csv_bytes(c, encoding=encoding)
            cb = _run_test(b, encoding=encoding)
            h = list(cb.get_hierarchy())
            self.assertEqual(len(h), 1)
            code, parent = h[0]
            self.assertEqual(parent, None)
            self.assertEqual(code.label, test1)
            label, = code.labels.all()
            self.assertEqual(label.label, test2)
            self.assertEqual(label.language.label, "test")

    def test_uuid(self):
        c = [("Code-1", "uuid"),
             ("x", "{acf728b0-e31a-11e2-a28f-0800200c9a66}")]

        b = _csv_bytes(c)
        cb = _run_test(b)
        id, = [c.id for c in cb.get_codes()]

        c = [("Code-1", "Code-2", "uuid"),
             ("y", "x", "{acf728b0-e31a-11e2-a28f-0800200c9a67}"),
             ("x", None, "{acf728b0-e31a-11e2-a28f-0800200c9a66}")]

        b = _csv_bytes(c)
        cb = _run_test(b)
        ids2 = [c.id for c in cb.get_codes()]
        self.assertIn(id, ids2)
        self.assertEqual(len(ids2), 2)
        self.assertEqual(len(set(ids2) - {id}), 1)
