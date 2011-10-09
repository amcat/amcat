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
    length = forms.IntegerField(initial=50, min_value=1, max_value=10000, widget=forms.HiddenInput, required=False)
    highlight = forms.BooleanField(initial=False, required=False)

class ArticleListScript(script.Script):
    input_type = None
    options_form = ArticleListForm
    output_type = script.ArticleIterator


    def run(self, input=None):
        """ returns an iterable of articles, when Solr is used, including highlighting """
        start = self.options['start'] or 0
        length = self.options['length'] or 50
        if length == -1: length = 999999 # unlimited (well, sort of ;)
        log.info('length %d' % length)
        if self.options['useSolr'] == False: # make database query
            return database.getQuerySet(**self.options)[start:length].select_related('medium')
        else:
            if self.options['highlight']:
                return solrlib.highlight(self.options['query'], start=start, length=length, filters=solrlib.createFilters(self.options))
            else:
                return solrlib.getArticles(self.options['query'], start=start, length=length, filters=solrlib.createFilters(self.options))
        
        
if __name__ == '__main__':
    cli.run_cli(ArticleListScript)