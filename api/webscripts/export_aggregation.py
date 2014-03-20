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
from webscript import WebScript
from amcat.scripts.searchscripts.aggregation import AggregationScript
import amcat.scripts.forms

    
class ExportAggregationForm(amcat.scripts.forms.TableOutputForm):
    pass
    # output = forms.ChoiceField(choices=(('csv', 'CSV'),('excel', 'Excel (.xslx)'),('spss', 'SPSS (.sav)'), ('html', 'HTML')), initial='csv')

class ExportAggregation(WebScript):
    name = "Export Aggregation"
    form_template = None
    form = ExportAggregationForm
    displayLocation = ('ShowAggregation')
    output_template = None
    is_download = True
    
    def run(self):
        aggrTable = AggregationScript(self.data).run()
        t = dict_to_columns(aggrTable)
        return self.outputResponse(t, AggregationScript.output_type, filename='Export Aggregation')
            


from amcat.tools.table import table3
from functools import partial
def dict_to_columns(table, rowheader_label="group", rowheader_type=str, cell_type=int):
    result = table3.ObjectTable(rows=table.getRows())
    result.addColumn(table3.ObjectColumn(label=rowheader_label, cellfunc = lambda row:row,
                                         fieldtype = rowheader_type))
    for col in table.getColumns():
        result.addColumn(table3.ObjectColumn(label=unicode(col), cellfunc = partial(table.getValue, column=col),
                                             fieldtype = cell_type))
    return result

    
