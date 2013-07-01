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


class FileUploadForm(forms.Form):
    """Helper form to handle uploading a file with encoding"""
    encoding = forms.ChoiceField(choices=enumerate(ENCODINGS),
                                 initial=0, required=False, 
                                 help_text="Try to change this value when character issues arise.", )
    file = forms.FileField(help_text="Uploading very large files can take a long time. If you encounter timeout problems, consider uploading smaller files")

    
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
