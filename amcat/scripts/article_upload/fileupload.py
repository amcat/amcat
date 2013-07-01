###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
Helper form for file upload forms that handles decoding and zip files
"""

from django import forms
import os.path
import shutil
import zipfile 
import chardet
import csv
import collections
from contextlib import contextmanager
from django.core.files import File
import tempfile

@contextmanager
def TemporaryFolder(*args, **kargs):
    tempdir = tempfile.mkdtemp(*args, **kargs)
    try:
        yield tempdir
    finally:
        shutil.rmtree(tempdir)
        
@contextmanager
def ZipFileContents(zip_file, *args, **kargs):
    with TemporaryFolder(*args, **kargs) as tempdir:
        with zipfile.ZipFile(zip_file) as zf:
            files = []
            for name in zf.namelist():
                fn = zf.extract(name, tempdir)
                files.append(File(open(fn), name=name))
            yield files
        
DecodedFile = collections.namedtuple("File", ["name", "file", "bytes", "encoding", "text"])
ENCODINGS = ["Autodetect", "ISO-8859-15", "UTF-8", "Latin-1"]


class RawFileUploadForm(forms.Form):
    """Helper form to handle uploading a file"""
    file = forms.FileField(help_text="Uploading very large files can take a long time. If you encounter timeout problems, consider uploading smaller files")

    def get_entries(self):
        return [self.files['file']]
    
class FileUploadForm(RawFileUploadForm):
    """Helper form to handle uploading a file with encoding"""
    encoding = forms.ChoiceField(choices=enumerate(ENCODINGS),
                                 initial=0, required=False, 
                                 help_text="Try to change this value when character issues arise.", )

    
    def decode(self, bytes):
        """
        Decode the given bytes using the encoding specified in the form.
        If encoding is Autodetect, use (1) utf-8, (2) chardet, (3) latin-1.
        Returns a tuple (encoding, text) where encoding is the actual encoding used.
        """
        enc = ENCODINGS[int(self.cleaned_data['encoding'] or 0)]
        if enc != 'Autodetect':
            return enc, bytes.decode(enc)
        try:
            return "utf-8", bytes.decode('utf-8')
        except UnicodeDecodeError:
            pass
        enc = chardet.detect(bytes)["encoding"]
        if enc:
            try:
                return enc, bytes.decode(enc)
            except UnicodeDecodeError:
                pass
        return 'latin-1', bytes.decode('latin-1')

    def decode_file(self, f):
        bytes = f.read()
        enc, text = self.decode(bytes)
        return DecodedFile(f.name, f, bytes, enc, text)

    def get_uploaded_text(self):
        """Returns a DecodedFile object representing the file"""
        return self.decode_file(self.files['file'])
        
    def get_entries(self):
        return [self.get_uploaded_text()]
    
DIALECTS = [("autodetect", "Autodetect"),
            ("excel", "CSV, comma-separated"),
            ("excel-semicolon", "CSV, semicolon-separated (Europe)"),
            ]

class excel_semicolon(csv.excel):
    delimiter = ';'
csv.register_dialect("excel-semicolon", excel_semicolon)

class CSVUploadForm(FileUploadForm):
    dialect = forms.ChoiceField(choices=DIALECTS, initial="autodetect", required=False, 
                                help_text="Select the kind of CSV file")

    def get_entries(self):
        return self.get_reader(reader_class=csv.DictReader)
    
    def get_reader(self, reader_class=csv.reader):
        
        f = self.files['file']
        d = self.cleaned_data['dialect']
        if not d: d = "autodetect"
        if d == 'autodetect':
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
        else:
            print "dialect: ",`d`
            dialect = csv.get_dialect(d)

        return reader_class(f, dialect=dialect)
    
class ZipFileUploadForm(FileUploadForm):
    file = forms.FileField(help_text="You can also upload a zip file containing the desired files. Uploading very large files can take a long time. If you encounter timeout problems, consider uploading smaller files")
        
    def get_uploaded_texts(self):
        """
        Returns a list of DecodedFile objects representing the zipped files,
        or just a [DecodedFile] if the uploaded file was not a .zip file.
        """
        f = self.files['file']
        extension = os.path.splitext(f.name)[1]
        if extension == ".zip":
            with ZipFileContents(f) as files:
                return [self.decode_file(f) for f in files]
        else:
            return [self.decode_file(f)]

    def get_entries(self):
        return self.get_uploaded_texts()

    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestFileUpload(amcattest.PolicyTestCase):

    def _get_entries(self, bytes, dialect="autodetect", encoding=0):
         with tempfile.NamedTemporaryFile() as f:
            f.write(bytes)
            f.flush()
            s = CSVUploadForm(dict(encoding=encoding, dialect=dialect),
                              dict(file=File(open(f.name))))
            if not s.is_valid():
                self.assertTrue(False, s.errors)

            return list(s.get_entries())
    
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
