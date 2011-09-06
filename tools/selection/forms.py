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
from amcat.model.project import Project
from amcat.model.user import User
from amcat.model.set import Set
from amcat.model.medium import Medium
from amcat.model.article import Article
from amcat.model.authorisation import Role, ProjectRole

#from amcat.tools.selection import webscripts


    
class AggregationForm(forms.Form):
    xAxis = forms.ChoiceField(choices=(('date', 'Date'), ('medium', 'Medium')))
    yAxis = forms.ChoiceField(choices=(('total', 'Total'), ('searchTerm', 'Search Term'), ('medium', 'Medium')))
    dateInterval = forms.ChoiceField(choices=(('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('quarter', 'Quarter'), ('year', 'Year')))
    
    def clean(self):
        cleanedData = self.cleaned_data
        
        return cleanedData
    
class ListForm(forms.Form):
    detailed = forms.BooleanField(initial=False, required=False)
    start = forms.IntegerField(initial=0, min_value=0, widget=forms.HiddenInput)
    count = forms.IntegerField(initial=100, min_value=1, max_value=10000, widget=forms.HiddenInput)

    
class SaveAsSetForm(forms.Form):
    setname = forms.CharField()
    project =  forms.ModelChoiceField(queryset=Project.objects.all()) # TODO: change to projects of user
