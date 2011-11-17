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

import amcat.scripts.output
from amcat.scripts import script, types
import inspect 

import logging
log = logging.getLogger(__name__)


outputClasses = {
    'json': types.JsonData,
    'csv': types.CsvData,
    'excel': types.ExcelData,
    'html': types.HtmlData,
    'spss': types.SPSSData,
    'datatables': types.DataTableJsonData
}

def findAllScripts():
    classes = inspect.getmembers(amcat.scripts.output, inspect.isclass)
    for classname, cls in classes:
        if hasattr(cls, 'input_type') and hasattr(cls, 'output_type'): # if the class is a Script
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
    log.warn('Script not found, input: %s output: %s. Scripts: %s' % (inputClass, outputClass, scripts))
    return None
            
            
scripts = list(findAllScripts())

