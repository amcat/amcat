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
from django.utils.datastructures import MultiValueDict

from amcat.models import Coding, CodingJob, CodingSchemaField, Label, CodingSchemaFieldType
from amcat.scripts.script import Script
from amcat.tools.table.table3 import Table, ObjectColumn

import logging
log = logging.getLogger(__name__)

import functools
import itertools

class CodingjobListForm(forms.Form):
    codingjobs = forms.ModelMultipleChoiceField(queryset=CodingJob.objects.all(), required=True)

    def __init__(self, data=None, **kwargs):
        """
        Offers a form with a list of codingjobs. Raises a KeyError if keyword-
        argument project is not given.
        
        @param project: Restrict list of codingjobs to this project
        @type project: models.Project"""
        self.project = kwargs.pop("project")

        super(CodingjobListForm, self).__init__(data, **kwargs)
        self.fields["codingjobs"].queryset = self.project.codingjob_set.all()
        self.data = self.data or MultiValueDict()

FIELD_LABEL = "{action} {s.label} (from {s.codingschema})"

class CodingJobResultsForm(CodingjobListForm):
    """
    This is a dynamically rendered form, which consists of a static part (general
    options for exporting results) and a dynamic part. The dynamic part consists of
    field options being generated for each of the fields in the union of all fields
    in all codingjobs, depending on their type.
    """
    unit_codings = forms.BooleanField(initial=False, required=False)
    include_duplicates = forms.BooleanField(initial=False, required=False)

    export_format = forms.ChoiceField(choices=({
        0 : "csv",
        1 : "xml"
        # etc?
    }).items())

    def __init__(self, data=None, **kwargs):
        """

        @param project: Restrict list of codingjobs to this project
        @type project: models.Project
        """
        codingjobs = kwargs.pop("codingjobs", None)
        super(CodingJobResultsForm, self).__init__(data, **kwargs)

        # Get all codingjobs and their fields
        unit_codings = self.fields["unit_codings"].clean(self.data.get("unit_codings"))
        codingjobs = self.fields["codingjobs"].clean(self.data.getlist("codingjobs", codingjobs))

        qfilter = "codingschema__codingjobs_{}__in"
        qfilter = qfilter.format("unit" if unit_codings else "article")

        # Get fields based on given codingjobs and unit_codings setting
        schemafields = (CodingSchemaField.objects.distinct("id").filter(**{
            qfilter : codingjobs
        })).order_by("id").select_related("codingschema", "fieldtype")

        # Insert dynamic fields
        self.fields.update(self.get_form_fields(schemafields))

    def get_form_fields(self, schemafields):
        """Returns a dict with all the fields needed to export this codingjob"""
        return dict(itertools.chain(*(self._get_form_fields(f) for f in schemafields)))

    def _get_form_fields(self, schemafield):
        """
        To prevent name collisions, this method also requires all schemafields, to check
        whether the current schemafield has a label which collides with a label of an
        other schemafield.
        """
        include_field = forms.BooleanField(
            label=FIELD_LABEL.format(action="Include", s=schemafield), initial=True
        )

        # Show 'include this field' checkbox (for every field)
        code_name = "schemafield_{s.id}".format(s=schemafield)
        yield ("{}_included".format(code_name), include_field)

        # Include field-specific form fields
        for code_name, field in get_fields(schemafield):
            yield (code_name, field)

def get_fields(schemafield):
    """
    Returns all additional form fields (if any) by looking up the function which
    generates them and executing it.
    """
    return GET_FIELDS_MAP.get(schemafield.fieldtype.name, lambda s : ())(schemafield)

def get_ontology_fields(schemafield):
    """Returns fields export_id and export_label for ontology field"""
    code_name = "schemafield_{s.id}".format(s=schemafield)

    # Export ids field
    yield ("{}_ids".format(code_name), forms.BooleanField(
        initial=True, label=FIELD_LABEL.format(s=schemafield, action="Export ids of")
    ))

    # Export labels field
    yield ("{}_labels".format(code_name), forms.BooleanField(
        initial=True, label=FIELD_LABEL.format(s=schemafield, action="Export labels of")
    ))

# Getting the fields from the database forces errors when starting
GET_FIELDS_MAP = {
    CodingSchemaFieldType.objects.get(name="DB ontology").name : get_ontology_fields
}


class GetCodingJobResults(Script):
    pass

