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

"""
Serialize a project to zipped RDF (e.g. for storage at DANS)
"""

from django import forms

from amcat.models import Coding, CodingJob, CodingSchemaField
from amcat.scripts.script import Script
from amcat.tools.table.table3 import Table

import logging
log = logging.getLogger(__name__)

class SerializeProject(Script):
    output_type = Table
    
    class options_form(forms.Form):
        job = forms.ModelChoiceField(queryset=CodingJob.objects.all(), required=True)
        unit_codings = forms.BooleanField(initial=False, required=False)
        
    def run(self, _input):
        job, unit_codings = self.options["job"], self.options["unit_codings"]
        schema = job.unitschema if unit_codings else job.articleschema
        fields = CodingSchemaField.objects.filter(codingschema=schema)

        codings = Coding.objects.filter(codingjob=job, sentence__isnull=(not unit_codings))

        return Table(columns=fields, rows=codings, cellfunc=Coding.get_value)
        

            
        
        

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
