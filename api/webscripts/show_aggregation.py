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
from django.template.loader import render_to_string
from django.utils import simplejson
from django.http import HttpResponse
from amcat.models.article import Article
from amcat.models.article import Medium
import time, calendar, datetime
from amcat.tools import table
from amcat.scripts import scriptmanager

from amcat.scripts.searchscripts.aggregation import AggregationScript, AggregationForm
import amcat.scripts.forms

TITLE_COLUMN_NAME = '0'


def get_key(obj):
    if hasattr(obj, 'id'):
        return obj.id
    return obj
    
class ShowAggregationForm(AggregationForm):
    outputType = forms.ChoiceField(choices=(
                    ('table', 'Table'), 
                    ('graph','Graph')
                  ), initial='table', required=False)
    graphOnly = forms.BooleanField(required=False, initial=False)

class ShowAggregation(WebScript):
    name = "Graph/Table"
    form_template = "api/webscripts/aggregationform.html"
    form = ShowAggregationForm
    output_template = None#'api/webscripts/aggregation.html'
    
    
    def run(self):
        aggrTable = AggregationScript(self.formData).run()
        if self.output == 'json-html' or (self.output == 'html' and self.options['graphOnly'] == True):
            datesDict = self.getDatesDict(aggrTable)
            dictToJsonCls = scriptmanager.findScript(dict, 'json')
            datesDictJson = dictToJsonCls().run(datesDict)
            
            columns = sorted(aggrTable.getColumns(), key=lambda x:x.id if hasattr(x,'id') else x)
            dataTablesHeaderDict = [{'mDataProp':TITLE_COLUMN_NAME,'sTitle':'', 'sType':'objid', 'sWidth':'100px'}] + \
                                    [{'mDataProp':get_key(col),'sTitle':col, 'sWidth':'70px'} for col in columns]
            columnsJson = dictToJsonCls().run(dataTablesHeaderDict)
            
            dataJson = []
            for row in aggrTable.getRows():
                rowJson = dict([(get_key(col), aggrTable.getValue(row, col)) for col in columns])
                rowJson[TITLE_COLUMN_NAME] = row
                dataJson.append(rowJson)
            dataJson = dictToJsonCls().run(dataJson)
            
            aggregationType = 'hits' if self.options['counterType'] == 'numberOfHits' else 'articles'
            graphOnly = 'true' if self.options['graphOnly'] == True else 'false'
        
            scriptoutput = render_to_string('api/webscripts/aggregation.html', { 
                                                'dataJson':dataJson, 
                                                'columnsJson':columnsJson,
                                                'aggregationType':aggregationType,
                                                'datesDict':datesDictJson,
                                                'graphOnly': graphOnly,
                                                'ownForm':self.form(self.formData)
                                             })
            if self.output == 'json-html':
                return self.outputJsonHtml(scriptoutput)
            else:
                return HttpResponse(scriptoutput, mimetype='text/html')
        else: # json-html output
            return self.outputResponse(aggrTable, AggregationScript.output_type)
            
            
    def getDatesDict(self, aggrTable):
        datesDict = {}
        
        if self.options['xAxis'] == 'date':
            dates = aggrTable.getRows()
            interval = self.options['dateInterval']
            if interval == 'week':
                for datestr in dates:
                    year = datestr.split('-')[0]
                    week = datestr.split('-')[1]
                    starttime = datetime.datetime.strptime('%s %s 1' % (year, week), '%Y %W %w')
                    endtime = datetime.datetime.strptime('%s %s 0' % (year, week), '%Y %W %w')
                    datesDict[datestr] = [starttime.strftime('%Y-%m-%d'), endtime.strftime('%Y-%m-%d')]
            elif interval == 'month':
                for datestr in dates:
                    year = int(datestr.split('-')[0])
                    month = int(datestr.split('-')[1])
                    endday = calendar.monthrange(year, month)[1]
                    datesDict[datestr] = ['%s-%02d-01' % (year, month), '%s-%02d-%02d' % (year, month, endday) ]
            elif interval == 'quarter':
                for datestr in dates:
                    year = datestr.split('-')[0]
                    quarter = int(datestr.split('-')[1])
                    startmonth = ((quarter - 1) * 3 + 1)
                    endmonth = ((quarter - 1) * 3 + 3)
                    endday = calendar.monthrange(int(year), endmonth)[1]
                    datesDict[datestr] = ['%s-%02d-01' % (year, startmonth), '%s-%02d-%02d' % (year, endmonth, endday)]
                    
        return datesDict
        
    # def outputNavigatorHtml(self, articles, stats=None):
        # actions = self.getActions()
        # return render_to_string('navigator/selection/articlesummary.html', { 'articles': articles, 'stats':stats, 'actions':actions, 'generalForm':self.generalForm, 'ownForm':self.ownForm})
        
