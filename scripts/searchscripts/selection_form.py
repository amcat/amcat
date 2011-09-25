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

#import inspect
import logging
log = logging.getLogger(__name__)


class ModelMultipleChoiceFieldWithIdLabel(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return "%s - %s" % (obj.id, obj.name)
        
class ModelChoiceFieldWithIdLabel(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "%s - %s" % (obj.id, obj.name)
        
class ArticleColumnsForm(forms.Form):
    columns = forms.MultipleChoiceField( # columns are used to indicate which columns should be loaded from the database (for performance reasons)
        choices=(
            ('articleid', 'Article ID'),
            ('date','Date'),
            ('mediumid','Medium ID'),
            ('mediumname','Medium Name'),
            ('projectid','Project ID'),
            ('projectname','Project Name'),
            ('pagenr','Page number'),
            ('section','Section'),
            ('length','Length'),
            ('url','url'),
            ('parentid','Parent Article ID'),
            ('externalid','External ID'),
            ('additionalMetadata','Additional Metadata'),
            ('headline','Headline'),
            ('text','Article Text')
        )
    )

class SelectionForm(forms.Form):
    projects = ModelMultipleChoiceFieldWithIdLabel(queryset=Project.objects.all()) # TODO: change to projects of user
    sets = ModelMultipleChoiceFieldWithIdLabel(queryset=Set.objects.none(), required=False)
    mediums = ModelMultipleChoiceFieldWithIdLabel(queryset=Medium.objects.none(), required=False)
    query = forms.CharField(widget=forms.Textarea, required=False)
    datetype = forms.ChoiceField(choices=(('all', 'All Dates'), ('before', 'Before'), ('after', 'After'), ('between', 'Between')))
    startDate = forms.DateField(input_formats=('%d-%m-%Y',), required=False)
    endDate = forms.DateField(input_formats=('%d-%m-%Y',), required=False)
    #action = forms.ChoiceField(choices=())
    #output = forms.CharField(required=False)
    
    def __init__(self, *args, **kwargs):
        super(SelectionForm, self).__init__(*args, **kwargs)
        if len(args) == 0:
            return
        projectids = args[0].getlist('projects') if hasattr(args[0], 'getlist') else args[0].get('projects')
        if type(projectids) != list:
            return
        projectids = map(int, projectids)
        #print args, projectids
        self.fields['sets'].queryset = Set.objects.filter(project__in=projectids)
        self.fields['mediums'].queryset = Medium.objects.filter(article__project__in=projectids).distinct().order_by('pk')
        
        #self.fields['action'].choices = ((ws.__name__, ws.name) for ws in webscripts.allScripts)#((classname, ws.name) for classname, ws in webscriptClasses )
    
    def clean(self):
        cleanedData = self.cleaned_data
        if cleanedData.get('datetype') in ('after', 'all') and 'endDate' in cleanedData:
            del cleanedData['endDate']
        if cleanedData.get('datetype') in ('before', 'all') and 'startDate' in cleanedData:
            del cleanedData['startDate']
        missingDateMsg = "Missing date"
        if 'endDate' in cleanedData and cleanedData['endDate'] == None: # if datetype in (before, between)
            self._errors["endDate"] = self.error_class([missingDateMsg])
            del cleanedData['endDate']
            #raise forms.ValidationError("Missing end date")
        if 'startDate' in cleanedData and cleanedData['startDate'] == None: # if datetype in (after, between)
            self._errors["startDate"] = self.error_class([missingDateMsg])
            del cleanedData['startDate']
            #raise forms.ValidationError("Missing start date")
        if cleanedData.get('query') == '':
            del cleanedData['query']
            cleanedData['useSolr'] = False
        else:
            cleanedData['useSolr'] = True
            
        # if 'output' not in cleanedData:
            # cleanedData['output'] = 'json-html'
            
        return cleanedData