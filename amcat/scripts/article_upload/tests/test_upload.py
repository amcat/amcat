import os
import zipfile
from contextlib import contextmanager

from amcat.scripts.article_upload.upload import UploadScript
from amcat.tools import amcattest

@contextmanager
def temporary_zipfile(files):
    from tempfile import mkstemp
    _, zipfn = mkstemp(prefix="upload_test", suffix=".zip")
    try:
        with zipfile.ZipFile(zipfn, mode="w") as f:
            for file in files:
                arcname = os.path.split(file)[-1]
                f.write(file, arcname=arcname)
        yield zipfn
    finally:
        os.remove(zipfn)



class TestUpload(amcattest.AmCATTestCase):
    def todo_test_zip_file(self):
        from tempfile import NamedTemporaryFile
        from django.core.files import File
        # does _get_units perform normally
        with NamedTemporaryFile(prefix=u"upload_test", suffix=".txt") as f:
            f.write("Test")
            f.flush()
            s = UploadScript(project=amcattest.create_test_project().id,
                             file=File(f))
            self.assertEqual({u.name for u in s._get_units()}, {f.name})

        # does a zip file work?

            #handle, fn = mkstemp(suffix=".zip")
        with NamedTemporaryFile(suffix=".zip") as f:
            with zipfile.ZipFile(f,  "w") as zf:
                zf.writestr("test.txt", "TEST")
                zf.writestr("x/test.txt", "TAST")

            s = UploadScript(project=amcattest.create_test_project().id,
                             file=File(f))
            self.assertEqual({f.name for f in s._get_units()}, {"test.txt", "x/test.txt"})
            self.assertEqual({f.read() for f in s._get_units()}, {"TEST", "TAST"})
