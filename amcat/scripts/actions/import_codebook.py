#!/usr/bin/python

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

import logging; log = logging.getLogger(__name__)

import csv
import os.path

from django import forms
from django.forms import widgets
from django.db import transaction

from amcat.scripts.script import Script
from django.db import transaction
from amcat.models import Code, Codebook, Language, Project

from amcat.scripts.article_upload.fileupload import CSVUploadForm

LABEL_PREFIX = "label"

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

    class options_form(CSVUploadForm):
        project = forms.ModelChoiceField(queryset=Project.objects.all())
        default_language = forms.ModelChoiceField(queryset=Language.objects.all(),
                                                  help_text="Language for new codes")
        codebook_name = forms.CharField(required=False)
        codebook = forms.ModelChoiceField(queryset=Codebook.objects.all(),
                                          help_text="Update existing codebook",
                                          required=False)
        
        def clean_codebook_name(self):
            """If codebook name is not specified, use file base name instead"""
            fn = None
            if self.files.get('file') and not self.cleaned_data.get('codebook_name'):
                fn =  os.path.splitext(os.path.basename(self.files['file'].name))[0]
            if fn:
                return fn
            return self.cleaned_data.get('codebook_name')
            

    @transaction.commit_on_success
    def _run(self, file, project, codebook_name, default_language, codebook, **kargs):
        data = csv_as_columns(self.bound_form.get_reader())
        
        # build code, parent pairs
        if "parent" in data:
            parents = zip(data["code"], data["parent"])
        else:
            cols = get_indented_columns(data)
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
        codes = {code : Code.get_or_create(uuid=uuid or None) for ((code, parent), uuid) in zip(parents, uuids)}

        to_add = []
        for code, parent in parents:
            instance = codes[code]
            parent_instance = codes[parent] if parent else None
            instance.add_label(default_language, code)
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
                      key = lambda k : int(k[len(prefix):]))
    return map(data.get, colnames)
            
def csv_as_columns(rows):
    """Read a csv file as a dictionary of name : [values] columns"""
    result = None
    for row in rows:
        if result is None:
            result = {name.lower() : [] for name in row.column_names}
        for name, val in row.items():
            result[name.lower()].append(val)
    return result

def get_index(cols, row):
    for i in range(len(cols)):
        try:
            if cols[i][row]:
                return i
        except IndexError:
            pass # incomplete rows
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
    #print result.output()


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest



def _run_test(bytes, **options):
    if 'project' not in options: options['project'] = amcattest.create_test_project().id
    if 'codebook_name' not in options: options['codebook_name'] = 'test'
    if 'default_language' not in options: options['default_language'] = 1
    from tempfile import NamedTemporaryFile
    from django.core.files import File
    with NamedTemporaryFile(suffix=".txt") as f:
        f.write(bytes)
        f.flush()

        return ImportCodebook(dict(file=File(open(f.name)), **options)).run()


def _csv_bytes(rows, encoding="utf-8", **kargs):
    def encode(x):
        if x is None or isinstance(x, str): return x
        return unicode(x).encode(encoding)    
    from cStringIO import StringIO
    out = StringIO()
    w = csv.writer(out, **kargs)
    for row in rows:
        w.writerow(map(encode, row))
    return out.getvalue()
    
    
class TestImportCodebook(amcattest.AmCATTestCase):


    def _standardize_cb(self, codebook, **kargs):
        """return a dense hierarchy serialiseation for easier comparisons"""
        return ";".join(sorted(set("{0}:{1}".format(*cp)
                                   for cp in codebook.get_hierarchy(**kargs))))
            
    def test_import(self):
        c = [("Code-1","Code-2","Code-3"),
             ("root",None, None),
             (None, "sub1", None),
             (None, None, u"sub1a")]
        b = _csv_bytes(c)
        self.assertEqual(self._standardize_cb(_run_test(b)), u"root:None;sub1:root;sub1a:sub1")
        
    def test_unicode(self):
        from amcat.scripts.article_upload.fileupload import ENCODINGS
        c = [("c1",),
             (u"code_\xe9",)]
        for encoding in ('UTF-8', 'Latin-1'):
            b = _csv_bytes(c, encoding=encoding)
            cb = _run_test(b, encoding=ENCODINGS.index(encoding))
            h = list(cb.get_hierarchy())
            self.assertEqual(len(h), 1)
            code, parent = h[0]
            self.assertEqual(parent, None)
            label, = code.labels.all()
            self.assertEqual(label.label, u"code_\xe9")

    def test_uuid(self):
        c = [("Code-1","uuid"),
             ("x", "{acf728b0-e31a-11e2-a28f-0800200c9a66}")]

        b = _csv_bytes(c)
        cb = _run_test(b)
        id,  = [c.id for c in cb.get_codes()]

        c = [("Code-1","Code-2","uuid"),
             ("y", "x", "{acf728b0-e31a-11e2-a28f-0800200c9a67}"),
             ("x", None, "{acf728b0-e31a-11e2-a28f-0800200c9a66}")]
        
        b = _csv_bytes(c)
        cb = _run_test(b)
        ids2 = [c.id for c in cb.get_codes()]
        self.assertIn(id, ids2)
        self.assertEqual(len(ids2), 2)
        self.assertEqual(len(set(ids2) - set([id])), 1)

