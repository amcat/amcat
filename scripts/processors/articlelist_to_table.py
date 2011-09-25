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
from amcat.scripts.searchscripts import selection_form


class ArticleListToTable(script.Script):
    input_type = script.ArticleIterator
    options_form = selection_form.ArticleColumnsForm
    output_type = table.table3.Table


    def run(self, articles):
        # if self.ownForm.cleaned_data['limitTextLength']:
            # textLambda = lambda a:a.text[:31900]
        # else:
        textLambda = lambda a:a.text
        colDict = { # mapping of names to article object attributes
            'articleid': table.table3.ObjectColumn("id", lambda a: a.id),
            'date': table.table3.ObjectColumn('Date', lambda a: a.date),
            'mediumid': table.table3.ObjectColumn('Medium ID', lambda a:a.medium_id),
            'mediumname': table.table3.ObjectColumn('Medium Name', lambda a:a.medium.name),
            'projectid': table.table3.ObjectColumn('Project ID', lambda a:a.project_id),
            'projectname': table.table3.ObjectColumn('Project Name', lambda a:a.project.name),
            'pagenr': table.table3.ObjectColumn('Page number', lambda a:a.pagenr),
            'section': table.table3.ObjectColumn('Section', lambda a:a.section),
            'length': table.table3.ObjectColumn('Length', lambda a:a.length),
            'url': table.table3.ObjectColumn('url', lambda a:a.url),
            'parentid': table.table3.ObjectColumn('Parent Article ID', lambda a:a.parent_id),
            'externalid': table.table3.ObjectColumn('External ID', lambda a:a.externalid),
            'additionalMetadata': table.table3.ObjectColumn('Additional Metadata', lambda a:a.metastring),
            'headline': table.table3.ObjectColumn('Headline', lambda a:a.headline),
            'text': table.table3.ObjectColumn('Article Text', textLambda)
        }
        #print self.options
        columns = [colDict[col] for col in self.options['columns']]
        
        tableObj = table.table3.ObjectTable(articles, columns)
        return tableObj
        
        