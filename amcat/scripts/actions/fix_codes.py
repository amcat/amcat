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

import logging; log = logging.getLogger(__name__)

from django import forms

#from amcat.tools import dbtoolkit
from amcat.scripts.script import Script
from amcat.models import CodingJob, CodingValue, Code, Project, CodingSchemaField

def get_fixed_code(labels, code_id):
    try:
        c = Code.objects.get(pk=code_id)
        for label in c.labels.all():
            lbl = label.label.strip().lower()
            if lbl in labels:
                return labels[lbl]
    except Code.DoesNotExist:
        return None

def fix_field(job, field):
    log.info("Fixing {field} in job {job.id}:{job}".format(**locals()))
    problems = set()
    field.codebook.cache()
    field.codebook.cache_labels()
    labels = {} # label -> code
    for c in field.codebook.get_codes():
        for label in c.labels.all():
            labels[label.label.strip().lower()] = c
    known_ids = {c.id for c in labels.values()}

    for cv in CodingValue.objects.filter(coding__codingjob=job, field=field):
        if cv.intval not in known_ids:
            fix = get_fixed_code(labels, cv.intval)
            log.info("Unknown code: {cv.intval} ({job}:{field}) --> {fix}".format(**locals()))
            if fix:
                cv.intval = fix.id
                cv.save()
            else:
                problems.add(cv.intval)

    return problems
    
class FixCodes(Script):
    """
    Checks whether the given job contains codes that do not occur in the
    codebook for the given field. If unknown codes are encountered, tries
    to replace them with a code from the codebook with the same label
    """
    
    class options_form(forms.Form):
        job = forms.ModelChoiceField(queryset=CodingJob.objects.all(), required=False)
        project = forms.ModelChoiceField(queryset=Project.objects.all(), required=False)
        field_name = forms.CharField()

    def _run(self, job, project, field_name):
        problems = set()

        if project:
            jobs = list(project.codingjob_set.all())
        elif job:
            jobs = [job]
        else:
            raise Exception("Please specify job or project")

        for job in jobs:
            try:
                field = job.articleschema.fields.get(label=field_name)
            except CodingSchemaField.DoesNotExist:
                continue
            
            problems |= fix_field(job, field)

        print
        if problems:
            print "The following codes could not be fixed:"
            for problem in problems:
                print problem
        else:
            print "All problems could be fixed"
            
    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
