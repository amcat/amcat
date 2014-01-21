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
import amcat.scripts.forms
from amcat.tools.table import table3
from functools import partial

class ExportAssociation(WebScript):
    name = "Export Association"
    form_template = None
    displayLocation = ('ShowAssociations')
    output_template = None
    is_download = True
    
    form = amcat.scripts.forms.TableOutputForm
    
    def run(self):
        from api.webscripts.associations import ShowAssociations
        table = ShowAssociations(data=self.data).get_table()
        table = self.get_table(table)

        return self.outputResponse(table, table3.Table, filename='Export Association')
            

    def get_table(self, assocTable, rowheader_label="interval", rowheader_type=str, cell_type=float):

        intervals = sorted({i for (i,q,q2,p) in assocTable})
        assocs = {(x,y) for (i,x,y,s) in assocTable}
        cols = {u"{x}\u2192{y}".format(x=x, y=y) : (x,y) for (x,y) in assocs}
        scores = {(i,x,y) : s for (i,x,y,s) in assocTable}

        colnames = sorted(cols)
        
        result = table3.ObjectTable(rows=intervals)
        result.addColumn(table3.ObjectColumn(label=rowheader_label, cellfunc = lambda row:row,
                                             fieldtype = rowheader_type))
        
        for col, (x,y) in sorted(cols.iteritems()):
            result.addColumn(table3.ObjectColumn(label=unicode(col), fieldtype=cell_type,
                                                 cellfunc = partial(getscore, scores, x, y)))
            
        return result

def getscore(scores, x, y, i):
    return scores.get((i, x, y))
