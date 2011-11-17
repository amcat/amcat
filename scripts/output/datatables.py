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

from amcat.tools.table import table3
from amcat.scripts import script, types
from django.utils import simplejson
from django import forms
import datetime


class DataTableForm(forms.Form):
    sEcho = forms.IntegerField(required=False)
    
    
import logging
log = logging.getLogger(__name__)

class TableToDatatable(script.Script):
    input_type = table3.Table
    options_form = DataTableForm
    output_type = types.DataTableJsonData


    def run(self, tableObj):
        tableData = []
        
        for row in tableObj.getRows():
            rowList = []
            for column in tableObj.getColumns():
                rowList.append(tableObj.getValue(row, column))
            tableData.append(rowList)
        dictObj = {}
        dictObj['aaData'] = tableData
        dictObj['iTotalRecords'] = 9999
        dictObj['iTotalDisplayRecords'] = 9999 if len(tableData) > 0 else 0
        dictObj['sEcho'] = self.options['sEcho']
        
        return simplejson.dumps(dictObj, default = lambda obj: obj.strftime('%d-%m-%Y') if isinstance(obj, datetime.datetime) else None)