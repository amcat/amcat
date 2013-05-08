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

from webscript import WebScript

from amcat.scripts.searchscripts.articlelist import ArticleListScript
from amcat.scripts.processors.articlelist_to_table import ArticleListToTable
from amcat.scripts.processors.associations import AssociationsScript
import amcat.scripts.forms

import logging
log = logging.getLogger(__name__)


class AssociationsForm(amcat.scripts.forms.InlineTableOutputForm):
    pass

class ShowAssociations(WebScript):
    name = "Associations"
    form_template = None
    form = AssociationsForm
    output_template = None
    solrOnly = True
    displayLocation = ('ShowSummary','ShowArticleList')
    
    
    def run(self):
        articleListFormData = self.formData.copy()
        articleListFormData['columns'] = 'hits' # need to add columns, since this is required for ArticleListScript 
        
        articles = ArticleListScript(articleListFormData).run()
        articleTable = ArticleListToTable({'columns':('hits', )}).run(articles)
        #print(articleTable.output())
        assocTable = AssociationsScript(self.formData).run(articleTable)
        return self.outputResponse(assocTable, AssociationsScript.output_type)
            
    
