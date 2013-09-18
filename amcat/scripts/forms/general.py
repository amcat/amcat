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

import logging
log = logging.getLogger(__name__)

__all__ = [
    "DateIntervalForm", "InlineTableOutputForm", "TableOutputForm",
    "GeneralColumnsForm", "ArticleColumnsForm"
]
        
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
        ('json-html', 'Show in navigator')
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
                ('author','Author'),
                ('length','Length'),
                ('url','url'),
                ('parent_id','Parent Article ID'),
                ('externalid','External ID'),
                ('additionalMetadata','Additional Metadata'),
                ('headline','Headline'),
                ('byline','Byline'),
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

