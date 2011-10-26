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

    
class ArticleidsForm(amcat.scripts.forms.SelectionForm):
    start = forms.IntegerField(initial=0, min_value=0, widget=forms.HiddenInput, required=False)
    length = forms.IntegerField(initial=50, min_value=1, max_value=9999999, widget=forms.HiddenInput, required=False)
    
    def clean_start(self):
        data = self.cleaned_data['start']
        if data == None:
            data = 0
        return data
        
    def clean_length(self):
        data = self.cleaned_data['length']
        if data == None:
            data = 50
        if data == -1:
            data = 999999 # unlimited (well, sort of ;)
        return data

class ArticleidsScript(script.Script):
    input_type = None
    options_form = ArticleidsForm
    output_type = script.ArticleidList


    def run(self, input=None):
        start = self.options['start']
        length = self.options['length']
        if self.options['useSolr'] == False: # make database query
            return database.getQuerySet(**self.options)[start:length].values_list('article_id', flat=True)
        else:
            return solrlib.articleids(self.options)

            
class ArticleidsDictScript(script.Script):
    input_type = None
    options_form = ArticleidsForm
    output_type = script.ArticleidDictPerQuery


    def run(self, input=None):
        if self.options['useSolr'] == False: # make database query
            raise Exception('This works only for Solr searches')
        else:
            return solrlib.articleidsDict(self.options)

        
        
if __name__ == '__main__':
    cli.run_cli(ArticleidsScript)