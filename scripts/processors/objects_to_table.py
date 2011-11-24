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
Script that converts a list of Article objects to a table
"""

from amcat.tools import table
from amcat.scripts import script, types
from amcat.tools.toolkit import dateToInterval
from django import forms
import amcat.scripts.forms
import logging
log = logging.getLogger(__name__)

class ObjectsToTableForm(amcat.scripts.forms.GeneralColumnsForm):
    pass

        
def getAttribute(object, column):
    if '.' in column:
        firstpart = column.split('.')[0]
        column = '.'.join(column.split('.')[1:])
        return getAttribute(getattr(object, firstpart), column)
    #log.info('%s %s' % (object, column))
    result = getattr(object, column)
    log.info('attr %s' % result)
    return result
        
def columnFunctionFactory(column):
    return lambda o: getAttribute(o, column)
        

class ObjectsToTable(script.Script):
    input_type = types.ObjectIterator
    options_form = ObjectsToTableForm
    output_type = table.table3.Table


    def run(self, objects):
        columns = []
        for column in self.options['columns']:
            columns.append(table.table3.ObjectColumn(column, columnFunctionFactory(column)))
        
        tableObj = table.table3.ObjectTable(objects, columns)
        
        return tableObj
        
        