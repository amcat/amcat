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
import re
import logging
log = logging.getLogger(__name__)

FORMATS = [
    ("0.12", False, "%1.2f"),
    ("0.123", False, "%1.3f"),
    ("12%", True, "%1.0f%%"),
    ("12.3%", True, "%1.1f%%"),
    ]

class AssociationsForm(forms.Form):
    network_output = forms.ChoiceField(choices=[('oo', 'Table'),
                                        ('ool', 'List'),
                                        ('oon', 'Network graph'),
                                        ])

    association_format = forms.ChoiceField(label="Number Format", choices = ((i, x[0]) for (i,x) in enumerate(FORMATS)), initial=0)
    
    graph_threshold = forms.DecimalField(label="Graph: threshold", required=False)
    graph_label = forms.BooleanField(label="Graph: include association in label", required=False)

    
    
class ShowAssociations(WebScript):
    name = "Associations"
    form_template = None
    form = AssociationsForm
    output_template = None
    solrOnly = True
    displayLocation = ('ShowSummary','ShowArticleList')


    def format(self, a):
        name, perc, formatstr = FORMATS[int(self.options["association_format"])]
        print `a`
        if perc: a*=100
        return formatstr % (a,)
        
        
    
    def run(self):
        articleListFormData = self.formData.copy()
        articleListFormData['columns'] = 'hits' # need to add columns, since this is required for ArticleListScript 
        
        articles = ArticleListScript(articleListFormData).run()
        articleTable = ArticleListToTable({'columns':('hits', )}).run(articles)
        #print(articleTable.output())
        assocTable = AssociationsScript(self.formData).run(articleTable)
        if self.options['network_output'] == 'ool':
            self.output = 'json-html'
            assocTable = table3.WrappedTable(assocTable, cellfunc = lambda a: self.format(a) if isinstance(a, float) else a)
            
            return self.outputResponse(assocTable, AssociationsScript.output_type)
        elif self.options['network_output'] == 'oo':
            # convert list to dict and make into dict table
            result = table3.DictTable()
            result.rowNamesRequired=True
            for x,y,a in assocTable:
                result.addValue(x,y,self.format(a))
            self.output = 'json-html'
            return self.outputResponse(result, AssociationsScript.output_type)
        elif self.options['network_output'] == 'oon':
            g = dot.Graph()
            threshold = self.options.get('graph_threshold')
            if not threshold: threshold = 0
            nodes = {}
            def getnode(x):
                if not x in nodes: 
                    id = "node_%i_%s" % (len(nodes), re.sub("\W","",x))
                    nodes[x] = dot.Node(id, x)
                return nodes[x]
                
            for x,y,a in assocTable:
                if threshold and a < threshold:
                    continue

                opts = {}
                if self.options['graph_label']: opts['label'] = self.format(a)
                w = 1 + 10 * a

                g.addEdge(getnode(x),getnode(y), weight=w, **opts)
            html = g.getHTMLObject()
            self.output = 'json-html'
            return self.outputResponse(html, unicode)
            
            
