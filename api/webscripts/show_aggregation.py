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

import calendar
import datetime
import json

from django import forms
from django.template.loader import render_to_string
from django.http import HttpResponse

from webscript import WebScript
from amcat.scripts import scriptmanager
from amcat.scripts.searchscripts.aggregation import AggregationScript, AggregationForm
from amcat.scripts.forms import SelectionForm


TITLE_COLUMN_NAME = 'x'


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
        selection = SelectionForm(project=self.project, data=self.data)
        selection.full_clean()
        aggrTable = AggregationScript(project=self.project, options=self.data, monitor=self.progress_monitor).run()
        if self.output == 'json-html' or (self.output == 'html' and self.options['graphOnly'] == True):

            columns = sorted(aggrTable.getColumns(), key=lambda x:x.id if hasattr(x,'id') else x)
            dataTablesHeaderDict = [{'mDataProp':TITLE_COLUMN_NAME,'sTitle':TITLE_COLUMN_NAME, 'sType':'objid', 'sWidth':'100px'}] + \
                                    [{'mDataProp':get_key(col),'mData':get_key(col),'sTitle':col, 'sWidth':'70px'} for col in columns]

            dataJson = []
            for row in aggrTable.getRows():
                rowJson = dict([(get_key(col), aggrTable.getValue(row, col)) for col in columns])
                rowJson[TITLE_COLUMN_NAME] = row
                dataJson.append(rowJson)
                
            if self.options['xAxis'] == 'date':
                datesDict = dict(_getDatesDict(aggrTable,  self.options['dateInterval']))
            else:
                datesDict = {}

            labels = {q.label : q.query for q in aggrTable.queries}
            aggregationType = 'articles'
            graphOnly = 'true' if self.options['graphOnly'] == True else 'false'

            scriptoutput = render_to_string('api/webscripts/aggregation.html', {
                                                'dataJson':json.dumps(dataJson),
                                                'columnsJson':json.dumps(dataTablesHeaderDict),
                                                'aggregationType':aggregationType,
                                                'datesDict': json.dumps(datesDict),
                                                'graphOnly': graphOnly,
                                                'labels' : json.dumps(labels),
                                                'ownForm':self.form(project=self.project, data=self.data),
                                                'relative':int(self.options['relative'])
                                             })


            if self.output == 'json-html':
                return self.outputJsonHtml(scriptoutput)
            else:
                return HttpResponse(scriptoutput, mimetype='text/html')
        else: # json-html output

            return self.outputResponse(aggrTable, AggregationScript.output_type)
            
            
from dateutil.relativedelta import relativedelta

DELTAS = {'month' : relativedelta(months=1),
          'quarter' : relativedelta(months=3),
          'year' : relativedelta(years=1),
          'week' : relativedelta(weeks=1),
          'day' : relativedelta(days=1),
          }

def _getDatesDict(aggrTable, interval):
    delta = DELTAS[interval]
    dates = aggrTable.getRows()
    for datestr in dates:
        date = datetime.datetime.strptime(datestr[:10], '%Y-%m-%d')
        end_date = date + delta
        yield (datestr, [date.isoformat(), end_date.isoformat()])

                
