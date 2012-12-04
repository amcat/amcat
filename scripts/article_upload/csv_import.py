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

    def split_text(self, text):

        return csv.DictReader(StringIO(text.encode('utf-8')))

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
            val = row[csvfield]
            if fieldname in PARSERS:
                val = PARSERS[fieldname](val)
            kargs[fieldname] = val

        return Article(**kargs)

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(CSV)
