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

from amcat.scripts import script
from amcat.scripts import cli
import amcat.scripts.forms
from amcat.tools.selection import solrlib, database
from django import forms
from amcat.tools.table.table3 import DictTable
from django.db.models import Sum, Count
from amcat.model.medium import Medium
from amcat.tools import table


class AggregationForm(forms.Form):
    xAxis = forms.ChoiceField(choices=(
                                ('date', 'Date'), 
                                ('medium', 'Medium')
                             ), initial = 'date')
    yAxis = forms.ChoiceField(choices=(
                            ('total', 'Total'), 
                            ('searchTerm', 'Search Term'), 
                            ('medium', 'Medium')
                         ), initial='medium')
    dateInterval = forms.ChoiceField(
                        choices=(
                            ('day', 'Day'), 
                            ('week', 'Week'), 
                            ('month', 'Month'), 
                            ('quarter', 'Quarter'), 
                            ('year', 'Year')
                        ), initial='month', required=False)
    counterType = forms.ChoiceField(choices=(
                        ('numberOfArticles', 'Number of Articles'), 
                        ('numberOfHits', 'Number of Hits')
                   ), initial='numberOfArticles')
    

class AggregationScriptForm(amcat.scripts.forms.SelectionForm, AggregationForm):
    pass
    
    
class AggregationScript(script.Script):
    input_type = None
    options_form = AggregationScriptForm
    output_type = table.table3.Table


    def run(self, input=None):
        """ returns a table containing the aggregations"""
        
        if self.options['useSolr'] == False: # make database query
            queryset = amcat.tools.selection.database.getQuerySet(**self.options)
            xAxis = self.options['xAxis']
            yAxis = self.options['yAxis']
            if xAxis == 'date':
                dateInterval = self.options['dateInterval']
                if not dateInterval: raise Exception('Missing date interval')
                dateStrDict = {'day':'YYYY-MM-DD', 'week':'YYYY-WW', 'month':'YYYY-MM', 'quarter':'YYYY-Q', 'year':'YYYY'}
                xSql = "to_char(date, '%s')" % dateStrDict[dateInterval] # notice: this might be Postgres specific SQL..
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

            # the following line will perform a group by database query
            data = queryset.extra(select=select_data).values(*vals).annotate(count=Count('id'))
            xDict = {}
            if xAxis == 'medium':
                xDict = Medium.objects.in_bulk(set(row['x'] for row in data))
            yDict = {}
            if yAxis == 'medium':
                yDict = Medium.objects.in_bulk(set(row['y'] for row in data))
            
            table3 = DictTable(0)
            table3.rowNamesRequired = True # make sure row names are printed
            for row in data:
                x = row['x']
                y = row.get('y', '[total]')
                count = row['count']
                table3.addValue(xDict.get(x, x), yDict.get(y, y), count)
            return table3
        else:
            #raise Exception("not implemented yet")
            queries = [x.strip() for x in self.options['query'].split('\n') if x.strip()]
            xAxis = self.options['xAxis']
            yAxis = self.options['yAxis']
            counterType = self.options['counterType']
            dateInterval = self.options['dateInterval']
            return solrlib.basicAggregate(queries, xAxis, yAxis, counterType, dateInterval, 
                                    filters=solrlib.createFilters(self.options))
            
        
        
if __name__ == '__main__':
    cli.run_cli(AggregationScript)