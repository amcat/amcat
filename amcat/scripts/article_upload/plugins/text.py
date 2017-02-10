#! /usr/bin/python
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
Plugin for uploading plain text files
"""

import logging
import os.path
import subprocess
import tempfile
from io import StringIO

from PyPDF2 import PdfFileReader
from django import forms

from amcat.models.article import Article
from amcat.scripts.article_upload.upload import UploadScript, UploadForm, ArticleField, _read, register_plugin
from amcat.tools import toolkit

log = logging.getLogger(__name__)


def _convert_docx(file):
    text, err = toolkit.execute("docx2txt", file.bytes)
    if not text.strip():
        raise Exception("No text from docx2txt. Error: {err}".format(**locals()))
    return text.decode("utf-8")


def _convert_doc(file):
    with tempfile.NamedTemporaryFile(suffix=".doc") as f:
        f.write(file.bytes)
        f.flush()
        text = subprocess.check_output(["antiword", f.name])
    if not text.strip():
        raise Exception("No text from {antiword?}")
    return text.decode("utf-8")


def _convert_pdf(file):
    _file = StringIO()
    _file.write(file.bytes)
    pdf = PdfFileReader(_file)
    text = ""
    n = pdf.getNumPages()
    for i in range(0,n):
        page = pdf.getPage(i)
        text += page.extractText()
    return text


def _convert_multiple(file, convertors):
    errors = []
    for convertor in convertors:
        return convertor(file)
    raise Exception("\n".join(errors))

@register_plugin()
class Text(UploadScript):
    """
    Plain text uploader.

    Please provide either the text of the article or upload a file. If a file is uploaded, the articleset name
    and headline will be taken from the file automatically. The filename can start with a date, in which case
    the date field can be left blank, for example: 2014-01-01_headline.txt.

    You can also upload a zip file containing multiple files. The articleset will be named after the zip file name,
    and the headlines (and optionally dates) will be taken from the individual file names. Any folders in the zip
    file will be entered in the 'section' field.

    Files in .docx, .doc, or .pdf format will be automatically converted to plain text.
    """

    class form_class(UploadForm):
        date = forms.DateField(required=False)
         
    @classmethod
    def get_fields(cls, file, encoding):
        path, fn = os.path.split(file.name)
        fn, ext = os.path.splitext(fn)
        yield ArticleField("Filename", "title", values=[fn])
        # FIXME encoding, and probably don't read the whole file?
        yield ArticleField("Text", "text", values=[file.read().decode("ascii")]) 
        if path: yield ArticleField("path", "section", values=[path])
        if "_" in fn:
            for i, elem in enumerate(fn.split("_")):
                yield ArticleField("Filename part {i}".format(**locals()), values=[elem])

    def get_headline_from_file(self):
        hl = self.options['file'].name
        if hl.endswith(".txt"): hl = hl[:-len(".txt")]
        return hl

    def parse_file(self, file, encoding, _data):
        dirname, filename = os.path.split(file)
        filename, ext = os.path.splitext(filename)

        def parse_field(file, type, value):
            if type == 'literal':
                return value
            if value == 'filename':
                return filename
            if value == 'text':
                return _read(file, encoding)
            if value.startswith('filename-'):
                n = int(value.split("-")[-1])
                return filename.split("_")[n-1]  # filename-n is 1 based index
            raise ValueError("Can't parse field {value}".format(**locals()))

        fields = {field: parse_field(file, **setting) for (field, setting) in self.options['field_map'].items()}
        return [Article(**fields)]

    def explain_error(self, error):
        """Explain the error in the context of unit for the end user"""
        name = getattr(error.unit, "name", error.unit)
        return "Error in file {name} : {error.error!r}".format(**locals())


if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli

    run_cli(handle_output=False)

