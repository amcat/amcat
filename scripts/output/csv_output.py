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
from amcat.scripts import script
import amcat.scripts.forms
from amcat.model.medium import Medium
from amcat.scripts.processors.articlelist_to_table import ArticleListToTable
import csv
from cStringIO import StringIO

class TableToCSV(script.Script):
    input_type = table3.Table
    options_form = None
    output_type = script.CsvStream


    def run(self, tableObj):
        buffer = StringIO()
        tableoutput.table2csv(tableObj, csvwriter=csv.writer(buffer, dialect='excel', delimiter=';'), writecolnames=True, writerownames=False, tabseparated=False)
        return buffer
       
       
# class DictToCSV(script.Script):
    # input_type = dict
    # options_form = None
    # output_type = script.CsvStream


    # def run(self, dictObj):
        # return simplejson.dumps(dictObj, default=encode_json)
       
       
class ArticleListToCSV(script.Script):
    input_type = script.ArticleIterator
    options_form = amcat.scripts.forms.ArticleColumnsForm
    output_type = script.CsvStream


    def run(self, articleList):
        tableObj = ArticleListToTable(self.options).run(articleList)
        return TableToCSV().run(tableObj)
        
        