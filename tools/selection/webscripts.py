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

import logging
log = logging.getLogger(__name__)
#DISPLAY_IN_MAIN_FORM = 'DisplayInMainForm'
    
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
                dateStr = dateStrDict[dateInterval]
                xSql = "to_char(date, '%s')" % dateStr
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
            table3 = DictTable(0)
            for row in data:
                table3.addValue(row['x'], row.get('y', 0), row['count'])
            log.debug(data)
            return table3
            # cursor = connection.cursor()
            # cursor.execute("SELECT count(%s) FROM articles WHERE projectid IN (%s)", [self.baz])
            # rows = cursor.fetchall()
        else:
            return None # not implemented yet
        
        
    def outputArticleList(self, articles):
        articles = articles[:50]
        return render_to_string('navigator/selection/articlelist.html', { 'articles': articles })
        
    
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
    template = None
    form = forms.AggregationForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        aggregateTable = self.getAggregates()
        return table2html(aggregateTable) #self.outputTable(aggregateTable)
    
    
        


class SaveAsSet(WebScript):
    name = "Save as set"
    template = None
    form = forms.SaveAsSetForm
    displayLocation = 'ShowTable'
    
    def run(self):
        pass
    