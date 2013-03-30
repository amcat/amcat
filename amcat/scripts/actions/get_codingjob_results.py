#!/usr/bin/python

##########################################################################
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

from django import forms

from amcat.models import Coding, CodingJob, CodingSchemaField, Label
from amcat.scripts.script import Script
from amcat.tools.table.table3 import Table, ObjectColumn

import logging
log = logging.getLogger(__name__)

import functools

class GetCodingJobResults(Script):
    """
    Extract the coded values for a coding job. This yields a Table with codings in the rows
    and in the columns the metadata followed by the coded fields. Values for metadata and
    codings are all primitives, e.g. code_id rather than code or unicode(code).
    """

    output_type = Table
    
    class options_form(forms.Form):
        job = forms.ModelChoiceField(queryset=CodingJob.objects.all(), required=True)
        unit_codings = forms.BooleanField(initial=False, required=False)
        deserialize_codes = forms.BooleanField(initial=False, required=False)
        
    def run(self, _input=None):
        job, unit_codings, deserialize = (self.options["job"], self.options["unit_codings"],
                                          self.options["deserialize_codes"])
        t = job.values_table(unit_codings)
        t.addColumn(lambda c : c.status_id, "Status", index=0)
        if unit_codings:
            t.addColumn(lambda c : c.sentence_id, "Sentence", index=0)
        t.addColumn(lambda c : c.article_id, "Article", index=0)
        t.addColumn(lambda c : c.codingjob_id, "Codingjob", index=0)

        if deserialize:
            deserialize_codes(t)

        deserialize_quality(job, unit_codings, t)

        return t

    def get_output_name(self):
        return "codingjob_{job.id}_{unit}codings".format(
            job=self.options["job"],
            unit="unit" if self.options["unit_codings"] else "article"
            )

def quality_cellfunc(field, coding):
    serialiser = field.fieldtype.serialiserclass(field)
    return serialiser.value_label(coding.get_value(field))

def deserialize_quality(job, unit_coding, table):
    schema = job.unitschema if unit_coding else job.articleschema
    fields = { f.label : f for f in schema.fields.all() }

    for col in [c for c in table.getColumns() if c.label in fields]:
        if fields[col.label].fieldtype.name != "Quality":
            continue

        # This field is of type QualitySerialiser
        col.cellfunc = functools.partial(
            quality_cellfunc, fields[col.label]
        )
        
def deserialize_codes(table):
    # identify code columns
    codes = {} # id : Code
    columns = set()
    for col in table.getColumns():
        try:
            f = col.field
        except AttributeError:
            continue
        if f.fieldtype.name == "DB ontology":
            columns.add(col)

    # gather code ids
    for col in columns:
        for row in table.getRows():
            codes[col.getCell(row)] = None
    # get labels
    for label in Label.objects.filter(code_id__in=codes.keys()).order_by("language"):
        if codes[label.code_id]: continue
        codes[label.code_id] = label.label
    # deserialize columns
    for i, col in list(enumerate(table.getColumns())):
        if col in columns:
            table.columns.insert(i, DeserializedFieldColumn(col, codes))


class DeserializedFieldColumn(ObjectColumn):
    def __init__(self, fieldcolumn, labels):
        super(DeserializedFieldColumn, self).__init__(label=fieldcolumn.label + "_label")
        self.fieldcolumn = fieldcolumn
        self.labels = labels
    def getCell(self, row):
        value = self.fieldcolumn.getCell(row)
        return self.labels.get(value, value)

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    t = cli.run_cli(handle_output=False)
    print t.to_csv()
