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

from django import forms
from django.forms import widgets
from django.db import transaction

from amcat.scripts.script import Script
from django.db import transaction
from amcat.models import Code, Codebook, Language, Project

from amcat.scripts.article_upload.fileupload import CSVUploadForm

LABEL_PREFIX = "label - "

        
    

class ImportCodebook(Script):
    """
    Import a codebook from a csv file.

    Structure should be indicated using either two columns labeled code and parent,
    or with n colunms labeled code-1 .. code-n (or c1 .. cn), which contain an
    indented structure.

    Optional columns are a uuid column and arbitrary many 'extra' labels which should be called
    'label - langauge'

    When using uuid, existing codes will be used where possible. Existing labels will not be overwritten
    but new labels will be added
    """

    class options_form(CSVUploadForm):
        codebook_name = forms.CharField()
        project = forms.ModelMultipleChoiceField(queryset=Project.objects.all())
        
    @transaction.commit_on_success
    def _run(self, file, **kargs):
        data = csv_as_columns(self.bound_form.get_reader())
        
        # build code, parent pairs
        if "parent" in data:
            raise Exception()
        else:
            cols = get_indented_columns(data)
            parents = list(get_parents_from_columns(cols))

        uuids = data["uuid"] if "uuid" in data else [None] * len(parents)

        # create objects
        
        cb = self.bound_form.save()
        log.info("Created codebook {cb.id} : {cb}".format(**locals()))

        codes = {code : Code.get_or_create(uuid=uuid) for ((code, parent), uuid) in zip(parents, uuids)}

        for code, parent in parents:
            instance = codes[code]
            cb.add_code(instance, parent=(parent and codes[parent]))
            if not instance.labels.all().exists():
                instance.add_label(0, code)

        for col in data:
            if col.startswith(LABEL_PREFIX):
                lang = col[len(LABEL_PREFIX):]
                try:
                    lang = int(lang)
                except ValueError:
                    lang = Language.objects.get(label=lang).id
                for (code, parent), label in zip(parents, data[col]):
                    if label and not codes[code].labels.filter(language_id=lang).exists():
                        codes[code].add_label(lang, label)
        

def get_indented_columns(data):
    prefix = 'code-' if 'code-1' in data else 'c'
    colnames = sorted((k for k in data if k.startswith(prefix)),
                      key = lambda k : int(k[len(prefix):]))
    return map(data.get, colnames)
            
def csv_as_columns(rows):
    """Read a csv file as a dictionary of name : [values] columns"""
    header = r.next()
    result = {name : [] for name in header}
    for row in r:
        row = row + [None] * (len(header) - len(row))
        for name, val in zip(header, row):
            result[name].append(val)
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

