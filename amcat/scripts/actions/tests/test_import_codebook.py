from amcat.scripts.actions.import_codebook import _csv_bytes, _run_test
from amcat.tools import amcattest


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
        from amcat.scripts.article_upload.fileupload import ENCODINGS

        c = [("c1",),
             (u"code_\xe9",)]
        for encoding in ('UTF-8', 'Latin-1'):
            b = _csv_bytes(c, encoding=encoding)
            cb = _run_test(b, encoding=ENCODINGS.index(encoding))
            h = list(cb.get_hierarchy())
            self.assertEqual(len(h), 1)
            code, parent = h[0]
            self.assertEqual(parent, None)
            label, = code.labels.all()
            self.assertEqual(label.label, u"code_\xe9")

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