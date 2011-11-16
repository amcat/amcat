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

import logging
log = logging.getLogger(__name__)

# class ArticleListSpecificForm(forms.Form):
    # start = forms.IntegerField(initial=0, min_value=0, widget=forms.HiddenInput)
    # length = forms.IntegerField(initial=30, min_value=1, max_value=10000, widget=forms.HiddenInput)
    
class ArticleListForm(amcat.scripts.forms.SelectionForm, amcat.scripts.forms.ArticleColumnsForm):
    start = forms.IntegerField(initial=0, min_value=0, widget=forms.HiddenInput, required=False)
    length = forms.IntegerField(initial=100, min_value=1, max_value=9999999, widget=forms.HiddenInput, required=False)
    highlight = forms.BooleanField(initial=False, required=False)
    sortColumn = forms.CharField(required=False)
    sortOrder = forms.ChoiceField(
                    choices=(
                        ('asc', 'Ascending'), 
                        ('desc', 'Descending'),
                     ),
                    initial = 'asc', required=False)
    
    def clean_start(self):
        data = self.cleaned_data['start']
        if data == None:
            data = 0
        return data
        
    def clean_length(self):
        data = self.cleaned_data['length']
        if data == None:
            data = 100
        if data == -1:
            data = 999999 # unlimited (well, sort of ;)
        return data
        
    def clean_columns(self):
        data = self.cleaned_data['columns']
        if self.cleaned_data['query'] == '' and ('keywordInContext' in data or 'hits' in data):
            self._errors["columns"] = self.error_class(['Keyword in Context and Hits columns require a query'])
        return data
        
    # def clean_sortColumn(self):
        # if self.cleaned_data['sortColumn'] in ('id', 'date', 'medium_id'):
            # return self.cleaned_data['sortColumn']
        # return None
        

class ArticleListScript(script.Script):
    input_type = None
    options_form = ArticleListForm
    output_type = script.ArticleIterator


    def run(self, input=None):
        """ returns an iterable of articles, when Solr is used, possibly including highlighting """
        start = self.options['start']
        length = self.options['length']
        
        if self.options['useSolr'] == False: # make database query
            qs = database.getQuerySet(**self.options)
            if self.options['sortColumn']:
                qs = qs.order_by(('-' if self.options['sortOrder'] == 'desc' else '') + self.options['sortColumn'])
            qs = qs[start:start+length].select_related('medium')
            return qs
        else:
            
            if self.options['highlight']:
                return solrlib.highlightArticles(self.options)
            else:
                return solrlib.getArticles(self.options)
        
        
if __name__ == '__main__':
    cli.run_cli(ArticleListScript)