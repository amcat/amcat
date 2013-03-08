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
Script that performs a query on the database or on Solr and returns a table with the aggregated data.
the x and y axis can be chosen. When using Solr the counter can be set to 'numberOfHits' to aggragate the hit count.
Also aggregation by searchTerm is Solr specific.
"""

from amcat.scripts import script
from amcat.scripts.tools import solrlib, database
import amcat.scripts.forms
from django import forms
from django.db.models import Sum, Count
from amcat.models.medium import Medium
from amcat.tools import table



class AggregationForm(amcat.scripts.forms.SelectionForm):
    """the form used by the Aggregation script"""
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

class AggregationScriptForm(AggregationForm, amcat.scripts.forms.SelectionForm):
    pass
    
    
class AggregationScript(script.Script):
    input_type = None
    options_form = AggregationScriptForm
    output_type = table.table3.Table


    def run(self, input=None):
        """ returns a table containing the aggregations"""
        
        if self.options['useSolr'] == False: # make database query
            queryset = database.getQuerySet(**self.options).distinct()
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
                xDict = Medium.objects.in_bulk(set(row['x'] for row in data)) # retrieve the Medium objects
            yDict = {}
            if yAxis == 'medium':
                yDict = Medium.objects.in_bulk(set(row['y'] for row in data)) # retrieve the Medium objects
            
            table3 = table.table3.DictTable(0) # the start aggregation count is 0
            table3.rowNamesRequired = True # make sure row names are printed
            for row in data:
                x = row['x']
                y = row.get('y', 'total')
                count = row['count']
                table3.addValue(xDict.get(x, x), yDict.get(y, y), count)
            return table3
        else:
            return solrlib.basicAggregate(self.options)
            
        
        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(AggregationScript)
