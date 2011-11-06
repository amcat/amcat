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

from amcat.tools import table
from amcat.scripts import script
from amcat.tools.toolkit import dateToInterval
from django import forms
import amcat.scripts.forms
import logging
log = logging.getLogger(__name__)

class ArticleListToTableForm(amcat.scripts.forms.ArticleColumnsForm):
    limitTextLength = forms.BooleanField(initial=True, required=False)

    
def lambdaHitFactory(query):
    return lambda a: a.hits.get(query)

class ArticleListToTable(script.Script):
    input_type = script.ArticleIterator
    options_form = ArticleListToTableForm
    output_type = table.table3.Table


    def run(self, articles):
        if self.options['limitTextLength'] == True:
            textLambda = lambda a:a.text[:31900]
        else:
            textLambda = lambda a:a.text
            
        hitsColumns = []
        if 'hits' in self.options['columns']:
            articles = list(articles)
            if not hasattr(articles[0], 'hits'):
                raise Exception('No hits attribute for article. Make sure you run a Solr query')
            for query in articles[0].hits.table.getColumns():
                hitsColumns.append(table.table3.ObjectColumn("Hit Count for: %s" % query[:100], lambdaHitFactory(query)))
        
        #log.info(hitsColumns)
        
        colDict = { # mapping of names to article object attributes
            'article_id': table.table3.ObjectColumn("Article ID", lambda a: a.id),
            'date': table.table3.ObjectColumn('Date', lambda a: a.date),
            'medium_id': table.table3.ObjectColumn('Medium ID', lambda a:a.medium_id),
            'medium_name': table.table3.ObjectColumn('Medium Name', lambda a:a.medium.name),
            'project_id': table.table3.ObjectColumn('Project ID', lambda a:a.project_id),
            'project_name': table.table3.ObjectColumn('Project Name', lambda a:a.project.name),
            'pagenr': table.table3.ObjectColumn('Page number', lambda a:a.pagenr),
            'section': table.table3.ObjectColumn('Section', lambda a:a.section),
            'length': table.table3.ObjectColumn('Length', lambda a:a.length),
            'url': table.table3.ObjectColumn('url', lambda a:a.url),
            'parent_id': table.table3.ObjectColumn('Parent Article ID', lambda a:a.parent_id),
            'externalid': table.table3.ObjectColumn('External ID', lambda a:a.externalid),
            'additionalMetadata': table.table3.ObjectColumn('Additional Metadata', lambda a:a.metastring),
            'headline': table.table3.ObjectColumn('Headline', lambda a:a.headline),
            'text': table.table3.ObjectColumn('Article Text', textLambda),
            'interval':table.table3.ObjectColumn('Interval', lambda a:dateToInterval(a.date, self.options['columnInterval'])),
            'keywordInContext': [table.table3.ObjectColumn('Context before', lambda a:a.keywordInContext['text']['before']), 
                                table.table3.ObjectColumn('Context hit', lambda a:a.keywordInContext['text']['hit']), 
                                table.table3.ObjectColumn('Context after', lambda a:a.keywordInContext['text']['after'])],
            'hits': hitsColumns
        }
        #print self.options
        columns = []
        for col in self.options['columns']:
            col = colDict[col] 
            if type(col) == list:
                for c in col:
                    columns.append(c)
            else:
                columns.append(col)
        
        tableObj = table.table3.ObjectTable(articles, columns)
        return tableObj
        
        