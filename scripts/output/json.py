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
from django.utils import simplejson
import amcat.scripts.forms
from amcat.model.medium import Medium
import datetime
from amcat.scripts.processors.articlelist_to_table import ArticleListToTable

def encode_json(obj):
    """ also encode Django objects to Json, preferebly by id-name""" 
    if isinstance(obj, Medium):
        return "%s - %s" % (obj.id, obj.name)
    if isinstance(obj, table3.Table):
        return simplejson.JSONDecoder().decode(TableToJson().run(obj)) # TODO: this is very ugly and inefficient.. (double encoding..)
    if isinstance(obj, datetime.datetime):
        return obj.strftime('%Y-%m-%d %H:%M')
    raise TypeError("%r is not JSON serializable" % (obj,))
    

class TableToJson(script.Script):
    input_type = table3.Table
    options_form = None
    output_type = types.JsonData


    def run(self, tableObj):
        return tableoutput.table2json(tableObj, colnames=True)
       
       
class DictToJson(script.Script):
    input_type = dict
    options_form = None
    output_type = types.JsonData


    def run(self, dictObj):
        return simplejson.dumps(dictObj, default=encode_json)
       
       
class ArticleListToJson(script.Script):
    input_type = types.ArticleIterator
    options_form = amcat.scripts.forms.ArticleColumnsForm
    output_type = types.JsonData


    def run(self, articleList):
        tableObj = ArticleListToTable(self.options).run(articleList)
        return tableoutput.table2json(tableObj, colnames=True)
        
        
        
class ErrormsgToJson(script.Script):
    input_type = types.ErrorMsg
    options_form = None
    output_type = types.JsonData
    
    def run(self, errorMsg):
        msgDict = {'message':errorMsg.message}
        if errorMsg.code:
            msgDict['code'] = errorMsg.code
        if errorMsg.fields:
            msgDict['fields'] = errorMsg.fields
        return simplejson.dumps({'error':msgDict})