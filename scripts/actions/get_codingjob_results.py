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

from amcat.models import Coding, CodingJob, CodingSchemaField
from amcat.scripts.script import Script
from amcat.tools.table.table3 import Table

import logging
log = logging.getLogger(__name__)

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
        
    def run(self, _input):
        job, unit_codings = self.options["job"], self.options["unit_codings"]
        t = job.values_table(unit_codings)
	t.addColumn(lambda c : c.status_id, "Status", index=0)
	if unit_codings:
	    t.addColumn(lambda c : c.sentence_id, "Sentence", index=0)
	t.addColumn(lambda c : c.article_id, "Article", index=0)
	t.addColumn(lambda c : c.codingjob_id, "Codingjob", index=0)
	
	return t
    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()

    
