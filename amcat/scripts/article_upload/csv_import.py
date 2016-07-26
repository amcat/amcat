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

from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.scripts.article_upload import fileupload
from amcat.scripts.article_upload.upload import UploadScript
from amcat.tools.toolkit import readDate
from navigator.views.articleset_upload_views import UploadWizardForm

FIELDS = ("text", "date", "medium", "pagenr", "section", "headline", "byline", "url", "externalid",
          "author", "addressee", "parent_url", "parent_externalid")
REQUIRED = {"text", "date"}

PARSERS = {
    "date": readDate,
    "pagenr": int,
    "externalid": int,
    "parent_externalid": int,
    "medium": Medium.get_or_create
}

HELP_TEXTS = {
    "parent_url": "Column name for the URL of the parent article, which should be in the same CSV file",
    "parent_externalid": "Column name for the External ID of the parent article, which should be in the same CSV file",
}


def is_nullable(field_name):
    try:
        return Article._meta.get_field(field_name).null
    except FieldDoesNotExist:
        return True




class CSVForm(UploadScript.options_form, fileupload.CSVUploadForm):
    medium_name = forms.CharField(
        max_length=Article._meta.get_field_by_name('medium')[0].max_length,
        required=False)
    medium_existing = forms.ModelChoiceField(
        queryset=Medium.objects.all(), required=False,
        help_text="Use this option if you want to choose one medium for all uploaded articles."
    )

    addressee_from_parent = forms.BooleanField(required=False, initial=False, label="Addressee from parent",
                                               help_text="If set, will set the addressee field to the author of the parent article")

    def clean_medium_name(self):
        cd = self.cleaned_data
        name = self.cleaned_data['medium_name']

        if not (name or ("medium" in self.data and self.data["medium"]) or "medium_existing" in cd):
            raise forms.ValidationError("Please specify either medium, medium_existing or medium_name")

        return name

    def __init__(self, *args, **kargs):
        super(CSVForm, self).__init__(*args, **kargs)
        for fieldname in reversed(FIELDS):
            required = fieldname in REQUIRED
            label = fieldname + " field"
            if fieldname in HELP_TEXTS:
                help_text = HELP_TEXTS[fieldname]
            else:
                help_text = "Column name for the article {}".format(fieldname)
                if not required:
                    help_text += ", or leave blank to leave unspecified"

            initial = fieldname if required else None

            field = forms.CharField(help_text=help_text, required=required,
                                    initial=initial, label=label)

            self.fields[fieldname] = field


    def clean_parent_url(self):
        idfield = self.cleaned_data['parent_url']
        if idfield and self.cleaned_data['parent_externalid']:
            raise forms.ValidationError("Cannot specify both external id and URL for parents")
        return idfield

    @classmethod
    def as_wizard_form(cls):
        return CSVWizardForm



class FileInfo:
    def __init__(self, file_name, file_fields):
        self.file_name = file_name
        self.file_fields = set(file_fields)

class BaseFieldMapFormSet(forms.BaseFormSet):
    def __init__(self, file_info=None, *args, **kwargs):
        initial = kwargs.pop('initial')
        if not initial:
            initial = self.get_initial(file_info)
        super().__init__(*args, initial=initial, **kwargs)
        self.file_info = file_info

    def get_initial(self, file_info: FileInfo):
        if file_info is None:
            return None
        return [{"field": field, "column": field}
                for field in self.get_fields() if field in file_info.file_fields]

    def _construct_form(self, i, **kwargs):
        return super()._construct_form(i, file_info=self.file_info, **kwargs)


    def clean(self):
        if any(self.errors):
            return

        errors = []
        existing = set(self.get_fields())
        required = set(self.get_required_fields())
        non_existent = []

        for form in self.forms:
            cleaned_data = form.cleaned_data
            if 'field' not in cleaned_data:
                continue
            required.discard(cleaned_data['field'])
            if cleaned_data['field'] not in existing and (not cleaned_data['create']):
                non_existent.append(cleaned_data['field'])
                errors.append("Dynamic fields not supported yet. Fill in an existing field.") #todo: allow dynamic fields

        if non_existent:
            errors.append("The following fields do not exist: '{}'.".format("', '".join(non_existent)))
        if required:
            errors.append("Field definitions for field(s) '{}' are required.".format("', '".join(required)))

        if errors:
            raise forms.ValidationError(errors)

    @property
    def cleaned_data(self):
        cleaned_data = super().cleaned_data
        field_dict = {d['field']: {k: v for k, v in d.items() if v and k != 'field'}
                      for d in cleaned_data if 'field' in d}
        return {"field_map": field_dict}

    def get_required_fields(self):
        return REQUIRED

    def get_fields(self):
        return FIELDS

    def non_field_errors(self):
        return self.non_form_errors()


class FieldMapForm(forms.Form):
    field = forms.CharField(max_length=100, help_text="The article field")
    column = forms.CharField(max_length=100, required=False,
                             help_text="The source column or field in the uploaded file")
    value = forms.CharField(max_length=200, required=False,
                            help_text="The literal value to assign to the field")
    create = forms.BooleanField(required=False, help_text="Create field if it does not exist")

    def __init__(self, *args, file_info=None, **kwargs):
        self.file_info = file_info
        super().__init__(*args, **kwargs)
        if file_info:
            self.fields['column'] = forms.ChoiceField(choices=[(None, "-- use single value --")] + [(field, field) for field in file_info.file_fields], required=False)


    def clean(self):
        cleaned_data = super().clean()
        if bool(cleaned_data['value']) == bool(cleaned_data['column']):
            raise forms.ValidationError("Fill in one of 'value' or 'column'")
        if self.file_info and cleaned_data['column'] and cleaned_data['column'] not in self.file_info.file_fields:
            raise forms.ValidationError("Field {} does not exist in file {}".format(cleaned_data['column'],
                                                                                    self.file_info.file_name))
        return cleaned_data


CSVFieldMapFormSet = forms.formset_factory(FieldMapForm, formset=BaseFieldMapFormSet, validate_max=False, extra=2)

class CSVWizardForm(UploadWizardForm):
    def __init__(self, inner_form=CSVForm, *args, **kwargs):
        super().__init__(inner_form)

    def get_form_list(self, inner_form):
        upload_form = super().get_form_list(inner_form)[0]
        upload_form.base_fields['dialect'] = inner_form.base_fields['dialect']
        field_form = CSVFieldMapFormSet
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

    def explain_error(self, error):
        if isinstance(error.error, KeyError):
            return "Field {error.error} not found in row {error.i}. Check field name and/or csv dialect".format(
                **locals())
        return super(CSV, self).explain_error(error)

    def run(self, *args, **kargs):

        if self.options['parent_url']:
            self.id_field, self.parent_field = 'url', 'parent_url'
        elif self.options['parent_externalid']:
            self.id_field, self.parent_field = 'externalid', 'parent_externalid'
        else:
            self.id_field, self.parent_field = None, None

        if self.parent_field:
            self.parents = {}  # id/url : id/url
            self.articles = {}  # id/url : article

        return super(CSV, self).run(*args, **kargs)

    @property
    def _medium(self):
        if self.options["medium"]:
            return

        if self.options['medium_existing']:
            return self.options['medium_existing']

        if self.options['medium_name']:
            med = Medium.get_or_create(self.options['medium_name'])
            self.options['medium_existing'] = med
            return med

        raise ValueError("No medium specified!")

    def parse_document(self, row):
        kargs = dict(medium=self._medium, metastring={})
        csvfields = [(fieldname, self.options[fieldname]) for fieldname in FIELDS if self.options[fieldname]]
        for fieldname, csvfield in csvfields:
            val = row[csvfield]
            if fieldname == 'date' and isinstance(val, datetime.datetime):
                pass  # no need to parse
            elif val.strip():
                if fieldname in PARSERS:
                    val = PARSERS[fieldname](val)
            elif is_nullable(fieldname):
                val = None
            else:
                val = val.strip()

            kargs[fieldname] = val

        # Metadata to metastring
        csvfields = [tup[1] for tup in csvfields]
        for key, value in row.items():
            if key not in csvfields:
                kargs["metastring"][key] = value

        kargs["metastring"] = json.dumps(kargs["metastring"])

        # In case medium wasn't defined in csv
        medium = self._medium
        if medium is not None:
            kargs["medium"] = medium

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
            for doc_id, parent_id in self.parents.items():
                doc = self.articles[doc_id]
                doc.parent = self.articles[parent_id]
                if not doc.addressee and self.options['addressee_from_parent']:
                    doc.addressee = doc.parent.author

                doc.save()
        super(CSV, self).postprocess(articles)


if __name__ == '__main__':
    from amcat.scripts.tools import cli

    cli.run_cli(CSV)

