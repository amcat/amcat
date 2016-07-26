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
import csv
import datetime
import json

import itertools
from django import forms
from django.db.models.fields import FieldDoesNotExist

from amcat.models import Article 
from amcat.scripts.article_upload import fileupload
from amcat.scripts.article_upload.upload import UploadScript, ParseError
from amcat.scripts.article_upload.upload_formtools import FieldMapFormSet, FileInfo
from amcat.tools.toolkit import readDate
from navigator.views.articleset_upload_views import UploadWizardForm


FIELDS = ("text", "date", "medium", "pagenr", "section", "headline", "byline", "url", "externalid",
          "author", "addressee", "parent_url", "parent_externalid")
REQUIRED = {"text", "date"}


TYPES = {
    "date": datetime.datetime,
    "pagenr": int,
    "externalid": int,
    "parent_externalid": int,
}

PARSERS = {
    datetime.datetime: readDate,
    int: int,
    str: str,
}

HELP_TEXTS = {
    "parent_url": "Column name for the URL of the parent article, which should be in the same CSV file",
    "parent_externalid": "Column name for the External ID of the parent article, which should be in the same CSV file",
}


def get_required():
    return REQUIRED

def get_fields():
    return FIELDS 

def get_field_type(field):
    return TYPES.get(field, str)

def get_parser(field_type):
    return PARSERS.get(field_type, lambda x: x)

class CSVForm(UploadScript.options_form, fileupload.CSVUploadForm):
    
    field_map = forms.CharField(max_length=2048, help_text='(JSON) dictionary consisting of "field":{"column":"<column name>"} or "field":{"value":"<value>"} mappings.') 

    addressee_from_parent = forms.BooleanField(required=False, initial=False, label="Addressee from parent",
                                               help_text="If set, will set the addressee field to the author of the parent article")



    def clean_field_map(self):
        cd = self.cleaned_data
        if isinstance(self.data['field_map'], dict):
            data = self.data['field_map']
        else:
            try:
                data = json.loads(cd['field_map'])
            except:
                raise forms.ValidationError('Field map should be a json string.')
        errors = []
        for k, v in data.items():
            if not isinstance(v, dict):
                errors.append(forms.ValidationError("Invalid field {}.".format(k)))
            if ('column' in v) == ('value' in v):
                errors.append(forms.ValidationError("Fill in exactly one of 'column' or 'value'."))

        if errors:
            raise forms.ValidationError(errors)
        return data

    def __init__(self, *args, **kargs):
        super(CSVForm, self).__init__(*args, **kargs)

    @classmethod
    def as_wizard_form(cls):
        return CSVWizardForm

class CSVWizardForm(UploadWizardForm):
    def __init__(self, inner_form=CSVForm, *args, **kwargs):
        super().__init__(inner_form)

    def get_form_list(self, inner_form):
        upload_form = super().get_form_list(inner_form)[0]
        upload_form.base_fields['dialect'] = inner_form.base_fields['dialect']
        field_form = FieldMapFormSet
        return [upload_form, field_form]

    class CSVUploadStepForm(UploadScript.options_form, fileupload.CSVUploadForm): pass

    @classmethod
    def get_upload_step_form(cls):
        return cls.CSVUploadStepForm


    @classmethod
    def get_file_info(cls, upload_form: fileupload.CSVUploadForm):
        try:
            reader = upload_form.get_reader()
        except csv.Error:
            raise
            return None
        try:
            firststep = next(reader)
        except StopIteration:
            return None

        return FileInfo(upload_form.cleaned_data['file'].name, firststep.column_names)

class CSV(UploadScript):
    """
    Upload CSV files to AmCAT.

    To tell AmCAT which columns from the csv file to use, you need to specify the name in the file
    for the AmCAT-fields that you want to import. So, if you have a 'title' column in the csv file
    that you want to import as the headline, specify 'title' in the "headline field" input box.

    Text and date and required, all other fields are optional.

    If you are encountering difficulties, please make sure that you know how the csv is exported, and
    manually set encoding and dialect in the options above.

    Since Excel has quite some difficulties with exporting proper csv, it is often better to use
    an alternative such as OpenOffice or Google Spreadsheet (but see below for experimental xlsx support).
    If you must use excel, there is a 'tools' button on the save dialog which allows you to specify the
    encoding and delimiter used.

    We have added experimental support for .xlsx files (note: only use .xlsx, not the older .xls file type).
    This will hopefully alleviate some of the problems with reading Excel-generated csv file. Only the
    first sheet will be used, and please make sure that the data in that sheet has a header row. Please let
    us know if you encounter any difficulties at github.com/amcat/amcat/issues. Since you can only attach
    pictures there, the best way to share the file that you are having difficulty with (if it is not private)
    is to upload it to dropbox or a file sharing website and paste the link into the issue.
    """

    options_form = CSVForm

    def run(self, *args, **kargs):
        return super(CSV, self).run(*args, **kargs)

    def parse_document(self, row):
        article = {}
        csvfields = self.options["field_map"]
        for fieldname, csvfield in csvfields.items():
            if 'column' in csvfield:
                colname = csvfield['column']
                val = row[colname]
            elif 'value' in csvfield:
                val = csvfield['value']
            
            if not val:
                article[fieldname] = None
                continue
            
            field_type = get_field_type(fieldname)
            if not isinstance(val, field_type):
                try:
                    val = get_parser(field_type)(val)
                except:
                    raise ParseError('Failed to parse value "{}". Expected {}.'.format(val, field_type.__name__)) 
            article[fieldname] = val


        for field in get_required():
            if field not in article or not article[field]: 
                raise ParseError('Missing value for required field "{}".'.format(field))        

        return Article(**article)
    
if __name__ == '__main__':
    from amcat.scripts.tools import cli

    cli.run_cli(CSV)

