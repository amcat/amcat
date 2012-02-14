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
Script that exports codingjobs to table
"""

from amcat.tools import table
from amcat.scripts import script, types
from amcat.tools.toolkit import dateToInterval
from django import forms
import amcat.scripts.forms
from amcat.models.coding.codingjob import CodingJob
import logging
log = logging.getLogger(__name__)

class CodingjobsForm(amcat.scripts.forms.TableOutputForm):
    codingjobs = amcat.scripts.forms.ModelMultipleChoiceFieldWithIdLabel(queryset=CodingJob.objects.all()) # TODO: change to codingjobs in projects of user

    
class ExportCodingjobsScript(script.Script):
    input_type = None
    options_form = CodingjobsForm
    output_type = table.table3.Table


    def run(self):
        
        tableObj = table.table3.DictTable(0)
        tableObj.columns.add(self.options['codingjobs'][0].name) #dummy data
        tableObj.rows.add('die bla')
        return tableObj
        
        