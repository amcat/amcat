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

from amcat.tools.table import tableoutput
from amcat.tools.table import table3
from amcat.scripts import script, types
import amcat.scripts.forms
from amcat.models.medium import Medium
from amcat.scripts.processors.articlelist_to_table import ArticleListToTable
import csv

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

def table_to_csv(table_obj, delimiter=","):
    """Convert a table3 object to a csv file (string)"""
    buff = StringIO()

    tableoutput.table2csv(table_obj, csvwriter=csv.writer(
        buff, dialect='excel', delimiter=delimiter),
        writecolnames=True, writerownames=False, tabseparated=False
    )

    return buff.getvalue()

def tableToCsv(tableObj, delimiter):
    return table_to_csv(tableObj, delimiter)
    
class TableToCommaCSV(script.Script):
    input_type = table3.Table
    options_form = None
    output_type = types.CsvCommaData


    def run(self, tableObj):
        return tableToCsv(tableObj, ',')
       
class TableToSemicolonCSV(script.Script):
    input_type = table3.Table
    options_form = None
    output_type = types.CsvSemicolonData


    def run(self, tableObj):
        return tableToCsv(tableObj, ';')
        
class ArticleListToSemicolonCSV(script.Script):
    input_type = types.ArticleIterator
    options_form = amcat.scripts.forms.ArticleColumnsForm
    output_type = types.CsvCommaData


    def run(self, articleList):
        tableObj = ArticleListToTable(self.options).run(articleList)
        return TableToCommaCSV().run(tableObj)
        
class ArticleListToCommaCSV(script.Script):
    input_type = types.ArticleIterator
    options_form = amcat.scripts.forms.ArticleColumnsForm
    output_type = types.CsvSemicolonData

    def run(self, articleList):
        tableObj = ArticleListToTable(self.options).run(articleList)
        return TableToSemicolonCSV().run(tableObj)
        
        
