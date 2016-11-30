#!/usr/bin/python

# ##########################################################################
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

import logging

import collections

import chardet
from django.core.files import File

log = logging.getLogger(__name__)

import csv
import os.path

from django import forms

from amcat.scripts.script import Script
from django.db import transaction
from amcat.models import Code, Codebook, Language, Project


LABEL_PREFIX = "label"
MAX_SAMPLE_SIZE = 1024
DIALECTS = [("autodetect", "Autodetect"),
            ("excel", "CSV, comma-separated"),
            ("excel-semicolon", "CSV, semicolon-separated (Europe)"),
            ]


class excel_semicolon(csv.excel):
    delimiter = ';'


csv.register_dialect("excel-semicolon", excel_semicolon)


def namedtuple_csv_reader(csv_file, encoding='utf-8', **kargs):
    """
    Wraps around a csv.reader object to yield namedtuples for the rows.
    Expects the first line to be the header.
    @params encoding: This encoding will be used to decode all values. If None, will yield raw bytes
     If encoding is an empty string or  'Autodetect', use chardet to guess the encoding
    @params object_name: The class name for the namedtuple
    @param kargs: Will be passed to csv.reader, e.g. dialect
    """
    if encoding.lower() in ('', 'autodetect'):
        encoding = chardet.detect(csv_file.read(MAX_SAMPLE_SIZE))["encoding"]
        log.info("Guessed encoding: {encoding}".format(**locals()))
        csv_file.seek(0)

    r = csv.reader(csv_file, **kargs)
    return namedtuples_from_reader(r, encoding=encoding)


def _xlsx_as_csv(file):
    """
    Supply a csv reader-like interface to an xlsx file
    """
    from openpyxl import load_workbook
    wb = load_workbook(file)
    ws = wb.get_sheet_by_name(wb.get_sheet_names()[0])
    for row in ws.rows:
        row = [c.value for c in row]
        yield row


def namedtuple_xlsx_reader(xlsx_file):
    """
    Uses openpyxl to read an xslx file and provide a named-tuple interface to it
    """
    reader = _xlsx_as_csv(xlsx_file)
    return namedtuples_from_reader(reader)


class CSVFile(File):
    def __init__(self, *args, dialect=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.dialect_name = dialect
        self._dialect = None

    @property
    def dialect(self):
        if self._dialect is not None:
            return self._dialect

        d = self.dialect_name or "autodetect"

        if d == 'autodetect':
            sample = self.file.read(MAX_SAMPLE_SIZE)
            dialect = csv.Sniffer().sniff(sample)
            self.file.seek(0)
            if dialect.delimiter not in "\t,;":
                dialect = csv.get_dialect('excel')
        else:
            dialect = csv.get_dialect(d)

        self._dialect = dialect
        return dialect

    def __iter__(self):
        reader = self.get_reader()
        yield from reader

    def get_reader(self, reader_class=namedtuple_csv_reader):
        file = self.file

        if file.name.endswith(".xlsx"):
            if reader_class != namedtuple_csv_reader:
                raise ValueError("Cannot handle xlsx files with non-default reader, sorry!")
            return namedtuple_xlsx_reader(file)


        return reader_class(file, dialect=self.dialect)


def namedtuples_from_reader(reader, encoding=None):
    """
    returns a sequence of namedtuples from a (csv-like) reader which should yield the header followed by value rows
    """

    header = next(iter(reader))

    class Row(collections.namedtuple("Row", header, rename=True)):
        column_names = header

        def __getitem__(self, key):
            if not isinstance(key, int):
                # look up key in self.header
                key = self.column_names.index(key)
            return super(Row, self).__getitem__(key)

        def items(self):
            return zip(self.column_names, self)

    for values in reader:
        if encoding is not None:
            values = [x.decode(encoding) if isinstance(x, bytes) else x for x in values]
        if len(values) < len(header):
            values += [None] * (len(header) - len(values))
        yield Row(*values)



class ImportCodebook(Script):
    """
    Import a codebook from a csv file.

    Structure should be indicated using either two columns labeled code and parent,
    or with n colunms labeled code-1 .. code-n (or c1 .. cn), which contain an
    indented structure.

    Optional columns are a uuid column and arbitrary many 'extra' labels which should be called
    'label - langauge' or 'label language' (e.g. "label - Dutch" or "label Dutch")

    When using uuid, existing codes will be used where possible. Existing labels will not be overwritten
    but new labels will be added

    Codes that do not exist yet will be added with the label from the code cell in the given language. This
    is in addition to any labels given in the 'label - language' columns.

    If an existing codebook is selected, that codebook will be updated instead of creating a new codebook.

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

    class options_form(forms.Form):
        file = forms.FileField(
            help_text="Uploading very large files can take a long time. If you encounter timeout problems, consider uploading smaller files")

        dialect = forms.ChoiceField(choices=DIALECTS, initial="autodetect", required=False,
                                    help_text="Select the kind of CSV file")
        project = forms.ModelChoiceField(queryset=Project.objects.all())
        codebook_name = forms.CharField(required=False)
        codebook = forms.ModelChoiceField(queryset=Codebook.objects.all(),
                                          help_text="Update existing codebook",
                                          required=False)

        def clean_codebook_name(self):
            """If codebook name is not specified, use file base name instead"""
            fn = None
            if self.files.get('file') and not self.cleaned_data.get('codebook_name'):
                fn = os.path.splitext(os.path.basename(self.files['file'].name))[0]
            if fn:
                return fn
            return self.cleaned_data.get('codebook_name')

        def get_entries(self):
            dialect = self.cleaned_data['dialect']
            return [CSVFile(self.get_uploaded_text(), dialect=dialect)]

    @transaction.atomic
    def _run(self, file, project, codebook_name, codebook, **kargs):
        data = csv_as_columns(self.bound_form.get_reader())

        if not data:
            raise ValueError("Couldn't read CSV data")
        # build code, parent pairs
        if "parent" in data:
            parents = zip(data["code"], data["parent"])
        else:
            cols = list(get_indented_columns(data))
            parents = list(get_parents_from_columns(cols))
        uuids = data["uuid"] if "uuid" in data else [None] * len(parents)

        # create codebook
        if not codebook:
            codebook = Codebook.objects.create(project=project, name=codebook_name)
            log.info("Created codebook {codebook.id} : {codebook}".format(**locals()))
        else:
            codebook.cache_labels()
            log.info("Updating {codebook.id} : {codebook}".format(**locals()))

        # create/retrieve codes
        codes = {}
        for ((code, parent), uuid) in zip(parents, uuids):
            try:
                c = Code.objects.get(uuid=uuid)
                if c.label != code:
                    c.label = code
                    c.save()
            except Code.DoesNotExist:
                c = Code.objects.create(uuid=uuid, label=code)
            codes[code] = c

        to_add = []
        for code, parent in parents:
            instance = codes[code]
            parent_instance = codes[parent] if parent else None
            cbc = codebook.get_codebookcode(instance)
            if cbc is None:
                to_add.append((instance, parent_instance))
            else:
                getid = lambda c: None if c is None else c.id
                if getid(cbc.parent) != getid(parent_instance):
                    cbc.parent = parent_instance
                    cbc.save()
        codebook.add_codes(to_add)

        for col in data:
            if col.startswith(LABEL_PREFIX):
                lang = col[len(LABEL_PREFIX):].strip()
                if lang.startswith('-'): lang = lang[1:].strip()
                try:
                    lang = int(lang)
                except ValueError:
                    lang = Language.get_or_create(label=lang).id
                for (code, parent), label in zip(parents, data[col]):
                    if label:
                        codes[code].add_label(lang, label)
        return codebook


def get_indented_columns(data):
    prefix = 'code-' if 'code-1' in data else 'c'
    prefix = 'code-' if 'code-1' in data else 'c'
    colnames = sorted((k for k in data if k.startswith(prefix)),
                      key=lambda k: int(k[len(prefix):]))
    return map(data.get, colnames)


def csv_as_columns(rows):
    """Read a csv file as a dictionary of name : [values] columns"""
    result = None
    for row in rows:
        if result is None:
            result = {name.lower(): [] for name in row.column_names}
        for name, val in row.items():
            result[name.lower()].append(val)
    return result


def get_index(cols, row):
    for i in range(len(cols)):
        try:
            if cols[i][row]:
                return i
        except IndexError:
            pass  # incomplete rows
    raise ValueError("Cannot parse row {row}".format(**locals()))


def get_parents_from_columns(cols):
    """Assuming cols are inented list, return a list of code, parent pairs in the same order as cols"""
    parents = []
    for i in range(len(cols[0])):
        j = get_index(cols, i)
        code = cols[j][i]
        parents = parents[:j]
        parent = parents[-1] if parents else None
        parents.append(code)
        yield code, parent


if __name__ == '__main__':
    from amcat.scripts.tools import cli

    result = cli.run_cli()

