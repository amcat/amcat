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

import os.path

from django import forms

from amcat.scripts.article_upload.upload import UploadScript

from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.tools.djangotoolkit import get_or_create
from amcat.tools import toolkit


class TextForm(UploadScript.options_form):
    medium = forms.ModelChoiceField(queryset=Medium.objects.all())
    headline = forms.CharField(required=False, help_text='If left blank, use filename (without extension and optional date prefix) as headline')
    date = forms.DateField(required=False, help_text='If left blank, use date from filename, which should be of form "yyyy-mm-dd_name"')
    section = forms.CharField(required=False, help_text='If left blank, use directory name')

    def __init__(self, *args, **kwargs):
        super(TextForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = sorted(self.fields.keyOrder, key=lambda f:f == "file")

        
class Text(UploadScript):
    options_form = TextForm

    def get_headline_from_file(self):
        hl = self.options['file'].name
        if hl.endswith(".txt"): hl = hl[:-len(".txt")]
        return hl

    def split_file(self, file):
        return [file]
    
    def parse_document(self, file):
        
        dirname, filename = os.path.split(file.name)
        filename, ext = os.path.splitext(filename)
        
        metadata = dict((k, v) for (k,v) in self.options.items()
                        if k in ["medium", "headline", "project", "date", "section"])
        if not metadata["date"]:
            datestring, filename = filename.split("_", 1)
            metadata["date"] = toolkit.read_date(datestring)
            
        if not metadata["headline"].strip():
            metadata["headline"] = filename

        if not metadata["headline"].strip():
            metadata["headline"] = filename
            
        if not metadata["section"].strip():
            metadata["section"] = dirname
            
        text = self.decode(file.read())
        return Article(text=text, **metadata)

if __name__ == '__main__':
    from amcat.tools import amcatlogging
    amcatlogging.debug_module("amcat.scripts.article_upload.upload")
    #amcatlogging.debug_module("amcat.scraping.scraper")
    from amcat.scripts.tools.cli import run_cli
    run_cli(handle_output=False)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
from amcat.tools import amcatlogging
amcatlogging.debug_module("amcat.scripts.article_upload.upload")

class TestUploadText(amcattest.PolicyTestCase):
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
            print File(open(f.name))
            a, = Text(dict(date='2010-01-01', headline='simple test',
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
            print a.section
            self.assertEqual(a.headline, fn.replace("1999-12-31_",""))
            self.assertEqual(a.date.isoformat()[:10], '1999-12-31')
            self.assertEqual(a.text, text)
