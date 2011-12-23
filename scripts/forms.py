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
from amcat.model.articleset import ArticleSet
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
        
        
class DateIntervalForm(forms.Form):
    interval = forms.ChoiceField(
            choices=(
                ('day', 'Day'), 
                ('week', 'Week'), 
                ('month', 'Month'), 
                ('quarter', 'Quarter'), 
                ('year', 'Year')
            ), initial='month')
        
class InlineTableOutputForm(forms.Form):
    """Form with all the possible outputs for a table3 object"""
    output = forms.ChoiceField(choices=(
        ('csv', 'CSV (semicolon separated)'),
        ('comma-csv', 'CSV (comma separated)'),
        ('excel', 'Excel (.xslx)'),
        ('spss', 'SPSS (.sav)'), 
        ('json-html', 'Inline HTML')
     ), initial='json-html')
        
class TableOutputForm(forms.Form):
    """Form with all the possible outputs for a table3 object"""
    output = forms.ChoiceField(choices=(
        ('csv', 'CSV (semicolon separated)'),
        ('comma-csv', 'CSV (comma separated)'),
        ('excel', 'Excel (.xslx)'),
        ('spss', 'SPSS (.sav)'), 
        ('html', 'HTML')
     ), initial='csv')
        
        
class GeneralColumnsForm(forms.Form):
    """represents column for any object, as a string seperated with ,"""
    columns = forms.CharField()

    def clean_columns(self):
        data = self.cleaned_data['columns']
        data = [x.strip() for x in data.split(',') if x.strip()]
        return data
        
        
class ArticleColumnsForm(forms.Form):
    columns = forms.MultipleChoiceField( # columns are used to indicate which columns should be loaded from the database (for performance reasons)
            choices=(
                ('article_id', 'Article ID'),
                ('hits', 'Hits'),
                ('keywordInContext', 'Keyword in Context'),
                ('date','Date'),
                ('interval', 'Interval'),
                ('medium_id','Medium ID'),
                ('medium_name','Medium Name'),
                ('project_id','Project ID'),
                ('project_name','Project Name'),
                ('pagenr','Page number'),
                ('section','Section'),
                ('length','Length'),
                ('url','url'),
                ('parent_id','Parent Article ID'),
                ('externalid','External ID'),
                ('additionalMetadata','Additional Metadata'),
                ('headline','Headline'),
                ('text','Article Text')
            ), initial = ('article_id', 'date', 'medium_id', 'medium_name', 'headline')
    )
    columnInterval = forms.ChoiceField(
            choices=(
                ('day', 'Day'), 
                ('week', 'Week'), 
                ('month', 'Month'), 
                ('quarter', 'Quarter'), 
                ('year', 'Year')
            ), initial='month', label='Column Interval', required=False)

            
            
class SearchQuery(object):
    """
    represents a query object that contains both a (Solr) query and an optional label
    """
    def __init__(self, query, label=None):
        self.query = query
        self.label = label or query
            
            
class SelectionForm(forms.Form):
    projects = ModelMultipleChoiceFieldWithIdLabel(queryset=Project.objects.order_by('-pk')) # TODO: change to projects of user
    articlesets = ModelMultipleChoiceFieldWithIdLabel(queryset=ArticleSet.objects.none(), required=False)
    mediums = ModelMultipleChoiceFieldWithIdLabel(queryset=Medium.objects.none(), required=False)
    query = forms.CharField(widget=forms.Textarea, required=False)
    articleids = forms.CharField(widget=forms.Textarea, required=False)
    datetype = forms.ChoiceField(choices=(('all', 'All Dates'), ('before', 'Before'), ('after', 'After'), ('between', 'Between')))
    startDate = forms.DateField(input_formats=('%d-%m-%Y',), required=False)
    endDate = forms.DateField(input_formats=('%d-%m-%Y',), required=False)
    # queries will be added by clean(), that contains a list of SearchQuery objects
    
    def __init__(self, *args, **kwargs):
        super(SelectionForm, self).__init__(*args, **kwargs)
        if len(args) == 0:
            return
        projectids = args[0].getlist('projects') if hasattr(args[0], 'getlist') else args[0].get('projects')
        if type(projectids) != list:
            return
        projectids = map(int, projectids)
        
        self.fields['articlesets'].queryset = ArticleSet.objects.order_by('-pk').filter(project__in=projectids)
        self.fields['mediums'].queryset = Medium.objects.filter(article__project__in=projectids).distinct().order_by('pk')
    
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
            cleanedData['queries'] = []
            queries = [x.strip() for x in cleanedData['query'].split('\n') if x.strip()] # split lines
            for query in queries:
                if '#' in query:
                    label = query.split('#')[0]
                    if len(label) == 0 or len(label) > 20:
                        self._errors["query"] = self.error_class(['Invalid query label (before the #)'])
                    query = query.split('#')[1]
                    if len(query) == 0:
                        self._errors["query"] = self.error_class(['Invalid query (after the #)'])
                else: 
                    label = None
                if '[' in query:
                    for query2 in cleanedData['queries']:
                        query = query.replace('[%s]' % query2.label, '(%s)' % query2.query)
                cleanedData['queries'].append(SearchQuery(query, label))
            
        try:
            cleanedData['articleids'] = [int(x.strip()) for x in cleanedData['articleids'].split('\n') if x.strip()]
        except:
            self._errors["articleids"] = self.error_class(['Invalid article ID list'])
        # if 'output' not in cleanedData:
            # cleanedData['output'] = 'json-html'
            
        return cleanedData
