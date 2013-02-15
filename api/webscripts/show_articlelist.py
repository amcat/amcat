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
from webscript import WebScript

from amcat.scripts.searchscripts.articlelist import ArticleListScript
from amcat.scripts.processors.articlelist_to_table import ArticleListToTable
import amcat.scripts.forms

from amcat.models import ArticleSet
from amcat.models import Project

import logging
log = logging.getLogger(__name__)

class ShowArticleListForm(amcat.scripts.forms.ArticleColumnsForm):
    outputTypeAl = forms.ChoiceField(choices=(
                    ('table', 'Table'), 
                    ('list','List with Snippets')
                  ), initial='table', required=False, label='Output As')
    
class ShowArticleList(WebScript):
    name = "Article List"
    form_template = "api/webscripts/articlelistform.html"
    form = ShowArticleListForm
    output_template = None 
    
    
    def run(self):
        formData = self.formData.copy() # copy needed since formData is inmutable
        if self.options['outputTypeAl'] == 'list':
            formData['highlight'] = True
        
        if "articlesets" not in formData:
            artsets = [str(aset.id) for aset in Project.objects.get(id=formData['projects']).all_articlesets()]
            formData.setlist("articlesets", artsets)

        articles = list(ArticleListScript(formData).run())

        if self.options['outputTypeAl'] == 'table':
            table = ArticleListToTable(self.formData).run(articles)
            self.output_template = 'api/webscripts/articletable.html'
            return self.outputResponse(table, ArticleListToTable.output_type)
        else:
            self.output_template = 'api/webscripts/articlelist.html'
            return self.outputResponse(articles, ArticleListScript.output_type)
        
