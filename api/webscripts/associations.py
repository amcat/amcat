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
from django import forms
from amcat.tools.table import table3
from amcat.tools import dot

import logging
log = logging.getLogger(__name__)


class AssociationsForm(forms.Form):
    network_output = forms.ChoiceField(choices=[('oo', 'Table'),
                                        ('ool', 'List'),
                                        ('oon', 'Network graph'),
                                        ])

    graph_threshold = forms.DecimalField(label="Graph: threshold", required=False)
    graph_label = forms.BooleanField(label="Graph: include association in label", required=False)
    
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
        if self.options['network_output'] == 'ool':
            self.output = 'json-html'
            return self.outputResponse(assocTable, AssociationsScript.output_type)
        elif self.options['network_output'] == 'oo':
            # convert list to dict and make into dict table
            result = table3.DictTable()
            result.rowNamesRequired=True
            for x,y,a in assocTable:
                result.addValue(x,y,a)
            self.output = 'json-html'
            return self.outputResponse(result, AssociationsScript.output_type)
        elif self.options['network_output'] == 'oon':
            g = dot.Graph()
            threshold = self.options.get('graph_threshold')
            if not threshold: threshold = 0
            for x,y,a in assocTable:
                a = float(a)
                print  `threshold`, `a`, a<threshold
                if threshold and a < threshold:
                    continue

                opts = {}
                if self.options['graph_label']: opts['label'] = a
                w = 1 + 10 * a
                
                g.addEdge(x,y, weight=w, **opts)
            html = g.getHTMLObject()
            self.output = 'json-html'
            return self.outputResponse(html, unicode)
            
            
