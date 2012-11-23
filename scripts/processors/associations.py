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
Script that will return a table with the associations between the queries.
Requires as input a table with as first column the interval, and as following columns the number of hits per query
"""

from amcat.scripts import script
import amcat.scripts.forms
from amcat.tools import table
from django import forms


import logging
log = logging.getLogger(__name__)


class AssociationsForm(forms.Form):
    pass # other form elements here


class AssociationsScript(script.Script):
    input_type = table.table3.Table
    options_form = AssociationsForm
    output_type = table.table3.Table


    def run(self, articleTable):
        queries = (c.label.replace('Hit Count for: ', '') for c in articleTable.getColumns())
        
        # start dummy code
        resultTable = table.table3.DictTable(0)
        resultTable.rowNamesRequired = True # make sure row names are printed
        for query in queries:
            resultTable.columns.add(query)
            resultTable.rows.add(query)
        return resultTable

        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(AssociationsScript)
    
