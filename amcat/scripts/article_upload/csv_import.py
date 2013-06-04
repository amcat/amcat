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

from amcat.models.article import Article
from amcat.models.medium import Medium, get_or_create_medium

from amcat.tools.toolkit import readDate

FIELDS = "text", "date", "pagenr", "section", "headline", "byline",  "url", "externalid"
REQUIRED = [True] * 2 + [False] * (len(FIELDS) - 2)
PARSERS = dict(date=readDate, pagenr=int, externalid=int)

class CSVForm(UploadScript.options_form):
    medium = forms.ModelChoiceField(queryset=Medium.objects.all(), required=False)
    medium_name = forms.CharField(
        max_length=Article._meta.get_field_by_name('medium')[0].max_length,
        required = False)

    def clean_medium_name(self):
        name = self.cleaned_data['medium_name']
        if not bool(name) ^ bool(self.cleaned_data['medium']):
            raise forms.ValidationError("Please specify either medium or medium_name")
        return name
    
    
    def __init__(self, *args, **kargs):
        super(CSVForm, self).__init__(*args, **kargs)
        for fieldname, required in zip(FIELDS, REQUIRED):
            label = fieldname + " field"
            help_text = "CSV Field name for the article {}".format(fieldname)
            if required:
                initial = fieldname
            else:
                initial = None
                help_text += ", or leave blank to leave unspecified"
    
            field = forms.CharField(help_text = help_text, required=required,
                                    initial=initial, label=label)
            self.fields.insert(0, fieldname, field)
    
    


class CSV(UploadScript):
    options_form = CSVForm

    def split_file(self, file):

        return csv.DictReader(file)

    @property
    def _medium(self):
        if self.options['medium']:
            return self.options['medium']
        if self.options['medium_name']:
            med = get_or_create_medium(self.options['medium_name'])
            self.options['medium'] = med
            return med
        raise ValueError("No medium specified!")
    
    def parse_document(self, row):
        kargs = dict(medium = self._medium)
        for fieldname in FIELDS:
            csvfield = self.options[fieldname]
            if not csvfield: continue
            val = self.decode(row[csvfield])
            if fieldname in PARSERS:
                val = PARSERS[fieldname](val)
                
            kargs[fieldname] = val

        return Article(**kargs)

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
            w.writerow([field.encode('utf-8') for field in row])
        f.flush()
            
        return CSV(dict(file=File(open(f.name)), encoding=0, project=p.id,
                        medium_name='testmedium', **options)).run()

class TestCSV(amcattest.PolicyTestCase):
    
    def test_csv(self):
        header = ('kop', 'datum', 'tekst')
        data = [('kop1', '2001-01-01', 'text1'), ('kop2', '10 maart 1980', 'text2')]
        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum")
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].headline, 'kop1')
        self.assertEqual(articles[1].date.isoformat()[:10], '1980-03-10')

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
