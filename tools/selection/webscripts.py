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

from amcat.tools.selection import forms
import amcat.tools.selection.database
import amcat.tools.selection.solrlib

from django.template.loader import render_to_string
from django.db import connection
    
from django.db.models import Sum, Count
from amcat.tools.table.table3 import DictTable
from amcat.tools.table.tableoutput import table2html
from amcat.model.medium import Medium

from django.utils import simplejson

import logging
log = logging.getLogger(__name__)
#DISPLAY_IN_MAIN_FORM = 'DisplayInMainForm'

def encode_json_medium(obj):
    if isinstance(obj, Medium):
        return "%s - %s" % (obj.id, obj.name)
    raise TypeError("%r is not JSON serializable" % (o,))
    
def get_key(obj):
    if hasattr(obj, 'id'):
        return obj.id
    return obj
    
class WebScript(object):
    name = None # the name of this webscript
    template = None # special markup to display the form
    form = None # fields specific for this webscript
    displayLocation = None # should be (a list of) another WebScript name that is displayed in the main form
    
    def __init__(self, generalForm, ownForm):
        self.generalForm = generalForm
        self.ownForm = ownForm
        
    def getArticles(self):
        """ returns an iterable of articles, when Solr is used, including highlighting """
        form = self.generalForm
        if form.cleaned_data['useSolr'] == False: # make database query
            return amcat.tools.selection.database.getQuerySet(**form.cleaned_data)
        else:
            return amcat.tools.selection.solrlib.highlight(form.cleaned_data['query'], filters=amcat.tools.selection.solrlib.createFilters(form.cleaned_data))
        
    def getAggregates(self):
        form = self.generalForm
        ownForm = self.ownForm
        if form.cleaned_data['useSolr'] == False: # make database query
            queryset = amcat.tools.selection.database.getQuerySet(**form.cleaned_data)
            xAxis = ownForm.cleaned_data['xAxis']
            yAxis = ownForm.cleaned_data['yAxis']
            if xAxis == 'date':
                dateInterval = ownForm.cleaned_data['dateInterval']
                dateStrDict = {'day':'YYYY-MM-DD', 'week':'YYYY-WW', 'month':'YYYY-MM', 'quarter':'YYYY-Q', 'year':'YYYY'}
                xSql = "to_char(date, '%s')" % dateStrDict[dateInterval]
            elif xAxis == 'medium':
                xSql = 'medium_id'
            else:
                raise Exception('unsupported xAxis')
                
            if yAxis == 'medium':
                ySql = 'medium_id'
            elif yAxis == 'total':
                ySql = None
            elif yAxis == 'searchTerm':
                raise Exception('searchTerm not supported when not performing a search')
            else:
                raise Exception('unsupported yAxis')
                
            select_data = {"x": xSql}
            vals = ['x']
            if ySql:
                select_data["y"] = ySql
                vals.append('y')

            
            data = queryset.extra(select=select_data).values(*vals).annotate(count=Count('id'))#.order_by('x')
            xDict = {}
            if xAxis == 'medium':
                xDict = Medium.objects.in_bulk(set(row['x'] for row in data))
            yDict = {}
            if yAxis == 'medium':
                yDict = Medium.objects.in_bulk(set(row['y'] for row in data))
            
            table3 = DictTable(0)
            for row in data:
                table3.addValue(xDict.get(row['x'], row['x']), yDict.get(row.get('y', '[total]'), row.get('y', '[total]')), row['count'])
            #log.debug(data)
            return table3
            # cursor = connection.cursor()
            # cursor.execute("SELECT count(%s) FROM articles WHERE projectid IN (%s)", [self.baz])
            # rows = cursor.fetchall()
        else:
            raise Exception("not implemented yet")
        
        
    def outputArticleList(self, articles):
        articles = articles[:50]
        return render_to_string('navigator/selection/articlelist.html', { 'articles': articles })
        
        
    def outputGraph(self, table):
        #return render_to_string('navigator/selection/table.html', { 'table': table })
        columns = sorted(table.getColumns(), key=lambda x:x.id if hasattr(x,'id') else x)
        columnsJson = simplejson.dumps([{'mDataProp':'[title]','sTitle':'', 'sType':'objid', 'sWidth':'100px'}] + [{'mDataProp':get_key(col),'sTitle':col, 'sWidth':'70px'} for col in columns], default=encode_json_medium)
        dataJson = []
        for row in table.getRows():
            rowJson = {get_key(col):table.getValue(row, col) for col in columns}
            rowJson['[title]'] = row
            dataJson.append(rowJson)
        dataJson = simplejson.dumps(dataJson, default=encode_json_medium)
            
        
        
        
    def outputTable(self, table):
        #return render_to_string('navigator/selection/table.html', { 'table': table })
        columns = sorted(table.getColumns(), key=lambda x:x.id if hasattr(x,'id') else x)
        columnsJson = simplejson.dumps([{'mDataProp':'[title]','sTitle':'', 'sType':'objid', 'sWidth':'100px'}] + [{'mDataProp':get_key(col),'sTitle':col, 'sWidth':'70px'} for col in columns], default=encode_json_medium)
        dataJson = []
        for row in table.getRows():
            rowJson = {get_key(col):table.getValue(row, col) for col in columns}
            rowJson['[title]'] = row
            dataJson.append(rowJson)
        dataJson = simplejson.dumps(dataJson, default=encode_json_medium)
            
        
        return """
        <table id="output-table"></table>
        <script type="text/javascript">
            var tableData = %s;
            var tableColumns = %s;
            
            function sortLabels(a, b){ // basic natural sort
                a = a.toLowerCase();
                var asplit = a.split(/(\-?[0-9]+)/g);
                b = b.toLowerCase();
                var bsplit = b.split(/(\-?[0-9]+)/g);
                for(var i=0; i<asplit.length; i++){
                    var diff = parseInt(asplit[i]) - parseInt(bsplit[i]);
                    if(isNaN(diff)){
                        diff = asplit[i].localeCompare(bsplit[i]);
                    }
                    if(diff != 0){
                        return diff;
                    }
                }
                return 0;
            }
            
            jQuery.fn.dataTableExt.oSort['objid-asc']  = function(a,b) {
                return sortLabels(a,b);
            };
            jQuery.fn.dataTableExt.oSort['objid-desc']  = function(a,b) {
                return sortLabels(b,a);
            };
            
            $(document).ready(function(){
                $('#output-table').dataTable( {
                    "aaData": tableData,
                    "aoColumns": tableColumns,
                    "bPaginate": false,
                    "bLengthChange": false,
                    "bFilter": false,
                    "bSort": true,
                    "bInfo": false
                } );
            });
            
            

        </script>
        """ % (dataJson, columnsJson)
        
    
class ShowList(WebScript):
    name = "Show list"
    template = None
    form = forms.ListForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        articles = self.getArticles()
        return self.outputArticleList(articles)
        
        
class ShowTable(WebScript):
    name = "Show table"
    template = "navigator/selection/tableform.html"
    form = forms.AggregationForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        aggregateTable = self.getAggregates()
        return self.outputTable(aggregateTable)
    
    
        
class ShowGraph(WebScript):
    name = "Show graph"
    template = "navigator/selection/tableform.html"
    form = forms.AggregationForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        aggregateTable = self.getAggregates()
        return self.outputGraph(aggregateTable)
    
    
        


class SaveAsSet(WebScript):
    name = "Save as set"
    template = None
    form = forms.SaveAsSetForm
    displayLocation = 'ShowTable'
    
    def run(self):
        pass
    