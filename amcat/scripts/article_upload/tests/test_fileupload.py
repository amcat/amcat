import tempfile
from django.core.files import File
from amcat.scripts.article_upload.fileupload import CSVUploadForm, namedtuple_csv_reader
from amcat.tools import amcattest


class TestFileUpload(amcattest.AmCATTestCase):

    def _get_entries(self, bytes, dialect="autodetect", encoding=0):
         with tempfile.NamedTemporaryFile() as f:
            f.write(bytes)
            f.flush()
            s = CSVUploadForm(dict(encoding=encoding, dialect=dialect),
                              dict(file=File(open(f.name))))
            if not s.is_valid():
                self.assertTrue(False, s.errors)

            return [dict(r.items()) for r in s.get_entries()]

    def _to_dict(self, rows):
        return [dict(r.items()) for r in rows]

    def test_csv(self):
        self.assertEqual(self._get_entries("a,b\n1,2", dialect="excel"),
                         [dict(a='1',b='2')])

        self.assertEqual(self._get_entries("a;b\n1;2", dialect="excel-semicolon"),
                         [dict(a='1',b='2')])

        # does autodetect work?
        self.assertEqual(self._get_entries("a,b\n1,2"),
                         [dict(a='1',b='2')])
        self.assertEqual(self._get_entries("a;b\n1;2"),
                         [dict(a='1',b='2')])

    def test_csv_reader(self):
        csv = ["a,b,c", "1,2,\xe9"]


        line, = namedtuple_csv_reader(csv, encoding='latin-1')
        self.assertEqual(tuple(line), ("1","2",u"\xe9"))

        self.assertEqual(line[0], "1")
        self.assertEqual(line.a, "1")
        self.assertEqual(line["a"], "1")

        csv = ["a\tb", "1", "\t2"]

        l1, l2 = namedtuple_csv_reader(csv, dialect='excel-tab')
        self.assertEqual(l1, ('1', None))
        self.assertEqual(l2, ('', '2'))