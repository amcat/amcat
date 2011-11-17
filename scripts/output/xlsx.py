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
from amcat.scripts.processors.articlelist_to_table import ArticleListToTable

from openpyxl.workbook import Workbook
from openpyxl.writer.dump_worksheet import ExcelDumpWriter
import zipfile
import io


class TableToXlsx(script.Script):
    input_type = table3.Table
    options_form = None
    output_type = types.ExcelData


    def run(self, tableObj):
        wb = Workbook(optimized_write = True)
        ws = wb.create_sheet()
        
        ws.append(([""] if tableObj.rowNamesRequired else []) + map(unicode, list(tableObj.getColumns()))) # write column names
        
        for row in tableObj.getRows():
            values = [unicode(row)] if tableObj.rowNamesRequired else []
            values += [tableObj.getValue(row, column) for column in tableObj.getColumns()]
            ws.append(values)
        writer = ExcelDumpWriter(wb)
        # need to do a little bit more work here, since the openpyxl library only supports writing to a filename, while we need a buffer here..
        #buffer = StringIO()
        buffer = io.BytesIO()
        zf = zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED)
        writer.write_data(zf)
        zf.close()
        buffer.flush()
        return buffer.getvalue()
       
       
       
class ArticleListToXlsx(script.Script):
    input_type = types.ArticleIterator
    options_form = amcat.scripts.forms.ArticleColumnsForm
    output_type = types.ExcelData


    def run(self, articleList):
        tableObj = ArticleListToTable(self.options).run(articleList)
        return TableToXlsx().run(tableObj)
        
        