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

from django import forms
from django.utils.datastructures import MultiValueDict

from amcat.models import Coding, CodingJob, CodingSchemaField, Label, CodingSchemaFieldType
from amcat.scripts.script import Script
from amcat.tools.table import table3

import logging
log = logging.getLogger(__name__)

import functools
import itertools

FIELD_LABEL = "{label} {schemafield.label} (from {schemafield.codingschema})"
            
class CodingjobListForm(forms.Form):
    codingjobs = forms.ModelMultipleChoiceField(queryset=CodingJob.objects.all(), required=True)

    def __init__(self, data=None, files=None, **kwargs):
        """
        Offers a form with a list of codingjobs. Raises a KeyError if keyword-
        argument project is not given.
        
        @param project: Restrict list of codingjobs to this project
        @type project: models.Project"""
        self.project = kwargs.pop("project")

        super(CodingjobListForm, self).__init__(data, files, **kwargs)
        self.fields["codingjobs"].queryset = self.project.codingjob_set.all()
        self.data = self.data or MultiValueDict()

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

    def __init__(self, data=None,  files=None, **kwargs):
        """

        @param project: Restrict list of codingjobs to this project
        @type project: models.Project
        """
        codingjobs = kwargs.pop("codingjobs", None)
        super(CodingJobResultsForm, self).__init__(data, files, **kwargs)

        # Get all codingjobs and their fields
        unit_codings = self.fields["unit_codings"].clean(self.data.get("unit_codings"))
        if not codingjobs:
            codingjobs = self.fields["codingjobs"].clean(self.data.getlist("codingjobs", codingjobs))

        # Insert dynamic fields based on schemafields
        self.schemafields = _get_schemafields(codingjobs, unit_codings)
        self.fields.update(self.get_form_fields(self.schemafields))

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
            label=FIELD_LABEL.format(label="Include", **locals()), initial=True, required=False,
        )

        
        # Show 'include this field' checkbox (for every field)
        code_name = "schemafield_{s.id}".format(s=schemafield)
        yield ("{}_included".format(code_name), include_field)

        # Include field-specific form fields
        for id, field in schemafield.serialiser.get_export_fields():
            field.label = FIELD_LABEL.format(label="Export "+field.label, **locals())
            id = "schemafield_{schemafield.id}_{id}".format(**locals())
            yield id, field

def _get_schemafields(codingjobs, unit_codings, **kargs):
    # Get fields based on given codingjobs and unit_codings setting
    qfilter = "codingschema__codingjobs_{}__in".format("unit" if unit_codings else "article")

    # Get fields based on given codingjobs and unit_codings setting
    return (CodingSchemaField.objects
            .filter(**{qfilter : codingjobs})
            .order_by("id").distinct()
            .select_related("codingschema", "fieldtype"))
    

class CodingColumn(table3.ObjectColumn):
    def __init__(self, field, label, function):
        self.function = function
        self.field = field
        label = self.field.label + label
        super(CodingColumn, self).__init__(label)
    def getCell(self, coding):
        value = coding.get_value(field=self.field)
        return self.function(value)

class GetCodingJobResults(Script):
    options_form = CodingJobResultsForm

    def _run(self, codingjobs, **kargs):
        codingjobs = list(CodingJob.objects.filter(pk__in=codingjobs).prefetch_related("codings__values"))
        
        # avoid using codings.filter since that will trigger new sql instead of using prefetched values
        codings = list(itertools.chain.from_iterable((c for c in job.codings.all() if c.sentence is None)
                                                     for job in codingjobs ))
        t = table3.ObjectTable(rows=codings)
        
        for schemafield in self.bound_form.schemafields:
            prefix = "schemafield_{schemafield.id}".format(**locals())
            if self.options[prefix+"_included"]:
                
                options = {k[len(prefix)+1:] :v for (k,v) in self.options.iteritems() if k.startswith(prefix)}
                for label, function in schemafield.serialiser.get_export_columns(**options):
                    t.addColumn(CodingColumn(schemafield, label, function))

                #print schemafield

        #print t.output(rownames=True)
        return t

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest



class TestGetCodingJobResults(amcattest.PolicyTestCase):

    def _get_results(self, jobs, options):
        """
        @param options: {field :{options}} -> include that field with those options
        """
        from django.utils.datastructures import MultiValueDict
        from amcat.forms import validate
        jobs = list(jobs)

        
        data = dict(codingjobs=[job.id for job in jobs],
                    export_format=[0],
                    )
        for field, opts in options.items():
            data["schemafield_{field.id}_included".format(**locals())] = [True]
            for k, v in opts.items():
                data["schemafield_{field.id}_{k}".format(**locals())] = [v]
            
        f = CodingJobResultsForm(data=MultiValueDict(data), project=jobs[0].project)
        validate(f)
        result = GetCodingJobResults(f).run()
        #print(result.output())
        return list(result.to_list())
    
    def test_results(self):
        codebook, codes = amcattest.create_test_codebook_with_codes()
        schema, codebook, strf, intf, codef = amcattest.create_test_schema_with_fields(codebook=codebook)
        job = amcattest.create_test_job(unitschema=schema, articleschema=schema, narticles=5)
        articles = list(job.articleset.articles.all())
        
        c = amcattest.create_test_coding(codingjob=job, article=articles[0])
        c.update_values({strf:"bla", intf:1, codef:codes["A1b"]})

        self.assertEqual(self._get_results([job], {strf : {}, intf : {}, codef : dict(ids=True)}),
                         [('bla', 1, codes["A1b"].id)])
        
        c = amcattest.create_test_coding(codingjob=job, article=articles[1])
        c.update_values({strf:"blx", intf:1, codef:codes["B1"]})
        self.assertEqual(set(self._get_results([job], {strf : {}, intf : {}, codef : dict(labels=True, parents=2)})),
                         {('bla', 1, "A", "A1", "A1b"), ('blx', 1, "B", "B1", "B1")})

        
    def test_nqueries(self):
        from amcat.tools import amcatlogging
        amcatlogging.setup()

        codebook, codes = amcattest.create_test_codebook_with_codes()
        schema, codebook, strf, intf, codef = amcattest.create_test_schema_with_fields(codebook=codebook)
        job = amcattest.create_test_job(unitschema=schema, articleschema=schema, narticles=5)
        articles = list(job.articleset.articles.all())
        
        amcattest.create_test_coding(codingjob=job, article=articles[0]).update_values({strf:"bla", intf:1, codef:codes["A1b"]})
        amcattest.create_test_coding(codingjob=job, article=articles[1]).update_values({strf:"bla", intf:1, codef:codes["A1b"]})
        amcattest.create_test_coding(codingjob=job, article=articles[2]).update_values({strf:"bla", intf:1, codef:codes["A1b"]})
        amcattest.create_test_coding(codingjob=job, article=articles[3]).update_values({strf:"bla", intf:1, codef:codes["A1b"]})
        amcattest.create_test_coding(codingjob=job, article=articles[4]).update_values({strf:"bla", intf:1, codef:codes["A1b"]})                        

        codingjobs = list(CodingJob.objects.filter(pk__in=[job.id]).prefetch_related("codings__values"))
        c = codingjobs[0].codings.all()[0]
        amcatlogging.debug_module('django.db.backends')
        with self.checkMaxQueries(6):
            list(self._get_results([job], {strf : {}, intf : {}}))


        with self.checkMaxQueries(6, output="print"):
            list(self._get_results([job], {strf : {}, intf : {}, codef : dict(ids=True)}))


        with self.checkMaxQueries(6, output="print"):
            list(self._get_results([job], {strf : {}, intf : {}, codef : dict(labels=True)}))

