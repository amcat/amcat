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
Contains functions that make it easier to find scripts
Later it can be extended with finding scripts that are stored in the database
"""

import amcat.scripts.output
from amcat.scripts import types
import inspect 

import logging
log = logging.getLogger(__name__)


outputClasses = {
    'json': types.JsonData,
    'comma-csv': types.CsvCommaData,
    'csv': types.CsvSemicolonData,
    'excel': types.ExcelData,
    'html': types.HtmlData,
    'spss': types.SPSSData,
    'datatables': types.DataTableJsonData
}

def findAllScripts():
    """iterates over all available scripts"""
    classes = inspect.getmembers(amcat.scripts.output, inspect.isclass)
    for _classname, cls in classes:
        if hasattr(cls, 'input_type') and hasattr(cls, 'output_type'): # if the class is a Script
            #log.debug('found script %s' % classname)
            yield cls


def findScript(inputClass, outputClass):
    """
    This function will try to find a script that can take argument inputClass as input
    and return outputClass
    It will return None if no script is found
    """
    if type(outputClass) in (str, unicode):
        if not outputClass in outputClasses:
            raise Exception('invalid output class: %s' % outputClass)
        outputClass = outputClasses[outputClass]
    log.debug('Finding script, input: %s output: %s' % (inputClass, outputClass))
    for script in scripts:
        if script.input_type == inputClass and script.output_type == outputClass:
            return script

    if not (inputClass is None or outputClass is None):
        log.warn('Script not found, input: %s output: %s. Scripts: %s' % \
                                        (inputClass, outputClass, scripts))
    return None
            
            
scripts = list(findAllScripts())



###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest
from amcat.tools import table

class TestScriptManager(amcattest.PolicyTestCase):
    def test_find(self):
        """Test whether we can find certain basic scripts"""  
        self.assertIsNotNone(scripts)        
        self.assertIsNotNone(findScript(table.table3.Table, 'csv'))
        self.assertIsNotNone(findScript(table.table3.Table, 'html'))
        self.assertIsNotNone(findScript(table.table3.Table, 'json'))
        self.assertRaises(Exception, findScript, table.table3.Table, 'not-exisiting-outputclass')

