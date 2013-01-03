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

import logging
log = logging.getLogger(__name__)

class ExportArticlesForm(amcat.scripts.forms.ArticleColumnsForm, amcat.scripts.forms.TableOutputForm):
    length = forms.ChoiceField(choices=((100,'100'),(1000,'1.000'),(10000,'10.000'),(100000,'100.000'),(9999999, 'No limit')), initial=1000)
    limitTextLength = forms.BooleanField(initial=True, required=False)
    

    
class ExportArticles(WebScript):
    name = "Export Articles"
    form_template = "api/webscripts/exportArticlesForm.html"
    form = ExportArticlesForm
    displayLocation = ('ShowSummary', 'ShowArticleList')
    output_template = None 
    
    
    def run(self):
        articles = ArticleListScript(self.formData).run()
        table = ArticleListToTable(self.formData).run(articles)

        return self.outputResponse(table, ArticleListToTable.output_type, filename='Export Articles')
