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
Plugin for uploading csv files
"""



from __future__ import unicode_literals, absolute_import

import csv
from cStringIO import StringIO

from django import forms

from amcat.scripts.article_upload.upload import UploadScript
from amcat.scripts.article_upload import fileupload

from amcat.models.article import Article
from amcat.models.medium import Medium

from amcat.tools.toolkit import readDate

FIELDS = ("text", "date", "pagenr", "section", "headline", "byline",  "url", "externalid",
          "author", "addressee", "parent_url", "parent_externalid")
REQUIRED = [True] * 2 + [False] * (len(FIELDS) - 2)

PARSERS = dict(date=readDate, pagenr=int, externalid=int, parent_externalid=int)

HELP_TEXTS = {
    "parent_url" : "Column name for the URL of the parent article, which should be in the same CSV file",
    "parent_externalid" : "Column name for the External ID of the parent article, which should be in the same CSV file",
    }

class CSVForm(UploadScript.options_form, fileupload.CSVUploadForm):
    medium = forms.ModelChoiceField(queryset=Medium.objects.all(), required=False)
    medium_name = forms.CharField(
        max_length=Article._meta.get_field_by_name('medium')[0].max_length,
        required = False)

    addressee_from_parent = forms.BooleanField(required=False, initial=False, label="Addressee from parent",
                                               help_text="If set, will set the addressee field to the author of the parent article")
    
    def clean_medium_name(self):
        name = self.cleaned_data['medium_name']
        if not bool(name) ^ bool(self.cleaned_data['medium']):
            raise forms.ValidationError("Please specify either medium or medium_name")
        return name
    
    def __init__(self, *args, **kargs):
        super(CSVForm, self).__init__(*args, **kargs)
        for fieldname, required in reversed(zip(FIELDS, REQUIRED)):
            label = fieldname + " field"
            if fieldname in HELP_TEXTS:
                help_text = HELP_TEXTS[fieldname]
            else:
                help_text = "Column name for the article {}".format(fieldname)
                if not required:
                    help_text += ", or leave blank to leave unspecified"

            initial = fieldname if required else None
    
            field = forms.CharField(help_text = help_text, required=required,
                                    initial=initial, label=label)
            self.fields.insert(7, fieldname, field)
    
    
    def clean_parent_url(self):
        idfield = self.cleaned_data['parent_url']
        if idfield and self.cleaned_data['parent_externalid']:
            raise forms.ValidationError("Cannot specify both external id and URL for parents")
        return idfield
        


class CSV(UploadScript):
    options_form = CSVForm

    def explain_error(self, error):
        if isinstance(error.error, KeyError):
            return "Field {error.error} not found in row {error.i}. Check field name and/or csv dialect".format(**locals())
        return super(CSV, self).explain_error(error)
    
    def run(self, *args, **kargs):

        if self.options['parent_url']:
            self.id_field, self.parent_field = 'url', 'parent_url'
        elif self.options['parent_externalid']:
            self.id_field, self.parent_field = 'externalid', 'parent_externalid'
        else:
            self.id_field, self.parent_field = None, None
            
        if self.parent_field:
            self.parents = {} # id/url : id/url
            self.articles = {} # id/url : article
        
        return super(CSV, self).run(*args, **kargs)
    
    @property
    def _medium(self):
        if self.options['medium']:
            return self.options['medium']
        if self.options['medium_name']:
            med = Medium.get_or_create(self.options['medium_name'])
            self.options['medium'] = med
            return med
        raise ValueError("No medium specified!")
    
    def parse_document(self, row):
        kargs = dict(medium = self._medium)
        for fieldname in FIELDS:
            csvfield = self.options[fieldname]
            if not csvfield: continue
            val = self.decode(row[csvfield])
            if val.strip():
                if fieldname in PARSERS:
                    val = PARSERS[fieldname](val)
            else:
                val = None
                
            kargs[fieldname] = val

        if self.parent_field:
            doc_id = kargs.get(self.id_field)
            parent_id = kargs.pop(self.parent_field)
            if parent_id:
                self.parents[doc_id] = parent_id
            
        article = Article(**kargs)

        if self.parent_field:
            self.articles[doc_id] = article
            
        return article

    def postprocess(self, articles):
        if self.parent_field:
            for doc_id, parent_id in self.parents.iteritems():
                doc = self.articles[doc_id]
                doc.parent = self.articles[parent_id]
                if not doc.addressee and self.options['addressee_from_parent']:
                    doc.addressee = doc.parent.author
                
                doc.save()

    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(CSV)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest



def _run_test_csv(header, rows, **options):
    p = amcattest.create_test_project()
    from tempfile import NamedTemporaryFile
    from django.core.files import File
    with NamedTemporaryFile(suffix=".txt") as f:
        w = csv.writer(f)
        for row in [header] + list(rows):
            w.writerow([field and field.encode('utf-8') for field in row])
        f.flush()
            
        return CSV(dict(file=File(open(f.name)), encoding=0, project=p.id,
                        medium_name='testmedium', **options)).run()

class TestCSV(amcattest.PolicyTestCase):
    
    def test_csv(self):
        header = ('kop', 'datum', 'tekst', 'pagina')
        data = [('kop1', '2001-01-01', 'text1', '12'), ('kop2', '10 maart 1980', 'text2', None)]
        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum", pagenr='pagina')
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].headline, 'kop1')
        self.assertEqual(articles[0].pagenr, 12)
        self.assertEqual(articles[1].date.isoformat()[:10], '1980-03-10')
        self.assertEqual(articles[1].pagenr, None)

    def test_parents(self):
        header = ('kop', 'datum', 'tekst', 'id', 'parent', 'van')
        data = [('kop1', '2001-01-01', 'text1', "7", "12", 'piet'), ('kop1', '2001-01-01', 'text1', "12", None, 'jan')]
        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum",
                                 externalid='id',  parent_externalid='parent', author='van')
        
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].parent, articles[1])
        self.assertEqual(articles[0].externalid, 7)
        self.assertEqual(articles[0].author, 'piet')
        self.assertEqual(articles[0].addressee, None)

        
        self.assertEqual(articles[1].parent, None)
        self.assertEqual(articles[1].externalid, 12)
        self.assertEqual(articles[1].author, 'jan')
        self.assertEqual(articles[1].addressee, None)

        
        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum",
                                 externalid='id',  parent_externalid='parent', author='van',
                                 addressee_from_parent=True)

        self.assertEqual(articles[0].author, 'piet')
        self.assertEqual(articles[0].addressee, 'jan')
        self.assertEqual(articles[1].author, 'jan')
        self.assertEqual(articles[1].addressee, None)
                
        

    def test_date_format(self):
        # Stump class to test future 'date format' option, if needed. Currently just checks that
        # a variety of formats load correctly. 
        header = "date", "text"

        for datestr, dateformat, expected in [
            ("2001-01-01", None, "2001-01-01"),
            ("10/03/80", None, "1980-03-10"),
            ("15/08/2008", None, "2008-08-15"),
            ]:
        
            data = [(datestr, "text")]
            a, = _run_test_csv(header, data, date="date", text="text")
            self.assertEqual(a.date.isoformat()[:10], expected)
