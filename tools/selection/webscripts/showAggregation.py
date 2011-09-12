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
from amcat.tools.selection.webscripts.webscript import WebScript


class AggregationForm(forms.Form):
    xAxis = forms.ChoiceField(choices=(('date', 'Date'), ('medium', 'Medium')))
    yAxis = forms.ChoiceField(choices=(('total', 'Total'), ('searchTerm', 'Search Term'), ('medium', 'Medium')), initial='medium')
    dateInterval = forms.ChoiceField(choices=(('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('quarter', 'Quarter'), ('year', 'Year')), initial='month')
    outputType = forms.ChoiceField(choices=(('table', 'Table'), ('graph','Graph')),initial='table')
    counterType = forms.ChoiceField(choices=(('numberOfArticles', 'Number of Articles'), ('numberOfHits', 'Number of Hits')), initial='numberOfArticles')
    
    # def clean(self):
        # cleanedData = self.cleaned_data
        
        # return cleanedData
    
    
class ShowAggregation(WebScript):
    name = "Aggregation"
    template = "navigator/selection/tableform.html"
    form = AggregationForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        aggregateTable = self.getAggregates()
        title = None
        if self.isIndexSearch == False:
            title = 'Article count'
        return self.outputAggregationTable(aggregateTable, title)
    
    