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

from __future__ import unicode_literals

import logging;
from django.core.exceptions import ValidationError

log = logging.getLogger(__name__)
import os.path, tempfile, subprocess

from django import forms

from amcat.scripts.article_upload.upload import UploadScript
from amcat.scripts.article_upload import fileupload

from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.tools import toolkit
from django.core.exceptions import ValidationError


class TextForm(UploadScript.options_form, fileupload.ZipFileUploadForm):
    file = forms.FileField(help_text="You can also upload a zip file containing the desired files. Uploading very large files can take a long time. If you encounter timeout problems, consider uploading smaller files", required=False)
    
    medium = forms.CharField(required=True)
    headline = forms.CharField(required=False, help_text='If left blank, use filename (without extension and optional date prefix) as headline')
    date = forms.DateField(required=False, help_text='If left blank, use date from filename, which should be of form "yyyy-mm-dd_name"')
    section = forms.CharField(required=False, help_text='If left blank, use directory name')
    text = forms.CharField(widget=forms.Textarea, required=False)
    
    def get_entries(self):
        if 'file' in self.files:
            return super(TextForm, self).get_entries()
        return [None]

    def clean_text(self):        
        text = self.cleaned_data.get("text")
        if not (text and text.strip()):
            if 'file' not in self.files:
                raise ValidationError("Please either upload a file or provide the text")
        return text
        
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

from PyPDF2 import PdfFileReader
import StringIO

def _convert_pdf(file):
    _file = StringIO.StringIO()
    _file.write(file.bytes)
    pdf = PdfFileReader(_file)
    text = ""
    for page in pdf.pages:
        text += page.extractText()
    return text

def _convert_multiple(file, convertors):
    errors = []
    for convertor in convertors:
        return convertor(file)
        try:
            return convertor(file)
        except Exception, e:
            log.exception("Error on converting {file.name} using {convertor}".format(**locals()))
            errors.append("{convertor}:{e}".format(**locals()))
    raise Exception("\n".join(errors)) 

class Text(UploadScript):
    """
    Plain text uploader.

    Please provide either the text of the article or upload a file. If a file is uploaded, the article set name
    and headline will be taken from the file automatically. The filename can start with a date, in which case
    the date field can be left blank, for example: 2014-01-01_headline.txt.

    You can also upload a zip file containing multiple files. The article set will be named after the zip file name,
    and the headlines (and optionally dates) will be taken from the individual file names. Any folders in the zip
    file will be entered in the 'section' field.

    Files in .docx, .doc, or .pdf format will be automatically converted to plain text.
    """
    options_form = TextForm

    def get_headline_from_file(self):
        hl = self.options['file'].name
        if hl.endswith(".txt"): hl = hl[:-len(".txt")]
        return hl
    
    def parse_document(self, file):
        if file:
            dirname, filename = os.path.split(file.name)
            filename, ext = os.path.splitext(filename)
        else:
            dirname, filename, ext = None, None, None

        metadata = dict((k, v) for (k,v) in self.options.items()
                        if k in ["headline", "project", "date", "section"])
        metadata["medium"] = Medium.get_or_create(self.options['medium'])
        
        if not metadata["date"]:
            datestring, filename = filename.split("_", 1)
            metadata["date"] = toolkit.read_date(datestring)
            
        if not metadata["headline"].strip():
            metadata["headline"] = filename

        if not metadata["headline"].strip():
            metadata["headline"] = filename
            
        if not metadata["section"].strip():
            metadata["section"] = dirname

        if file:
            convertors = None
            if ext.lower() == ".docx":
                convertors = [_convert_docx, _convert_doc]
            elif ext.lower() == ".doc":
                convertors = [_convert_doc, _convert_docx]
            elif ext.lower() == ".pdf":
                convertors = [_convert_pdf]

            if convertors:
                text = _convert_multiple(file, convertors)
            else:
                text = file.text
        else:
            text = self.options['text']
            
        return Article(text=text, **metadata)

    def explain_error(self, error):
        """Explain the error in the context of unit for the end user"""
        name = getattr(error.unit, "name", error.unit)
        return "Error in file {name} : {error.error!r}".format(**locals())
    
if __name__ == '__main__':
    from amcat.tools import amcatlogging
    amcatlogging.debug_module("amcat.scripts.article_upload.upload")
    from amcat.scripts.tools.cli import run_cli
    run_cli(handle_output=False)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
import unittest
from amcat.tools import amcatlogging
amcatlogging.debug_module("amcat.scripts.article_upload.upload")

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
            self.assertEqual(a.headline, fn.replace("1999-12-31_",""))
            self.assertEqual(a.date.isoformat()[:10], '1999-12-31')
            self.assertEqual(a.text, text)

    def test_zip(self):
        from tempfile import NamedTemporaryFile
        from django.core.files import File
        import zipfile
        
        base = dict(project=amcattest.create_test_project().id,
                    articleset=amcattest.create_test_set().id,
                    medium=amcattest.create_test_medium().id)

        
        with NamedTemporaryFile(prefix=u"upload_test", suffix=".zip") as f:
            with zipfile.ZipFile(f, "w") as zf:
                zf.writestr("headline1.txt", "TEXT1")
                zf.writestr("x/headline2.txt", "TEXT2")
            f.flush()
            
            s = Text(file=File(f),date='2010-01-01', **base)
            arts = s.run()
            self.assertEqual({a.headline for a in arts}, {"headline1","headline2"})
            self.assertEqual({a.section for a in arts}, {'',"x"})
            self.assertEqual({a.text for a in arts}, {"TEXT1", "TEXT2"})
            
