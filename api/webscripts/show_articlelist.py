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
from amcat.tools import keywordsearch

import logging
log = logging.getLogger(__name__)

class ShowArticleListForm(amcat.scripts.forms.ArticleColumnsForm):
    outputTypeAl = forms.ChoiceField(choices=(
                    ('table', 'Table'), 
                    ('list','List with Snippets')
                  ), initial='table', required=False, label='Output As')

FORM_FIELDS_TO_ELASTIC = {'article_id' : "id", "medium_name" : "medium", "medium_id" : "mediumid" }
    
class ShowArticleList(WebScript):
    name = "Article List"
    form_template = "api/webscripts/articlelistform.html"
    form = ShowArticleListForm
    output_template = None 
    
    
    def run(self):
        formData = self.data.copy() # copy needed since formData is inmutable
        if self.options['outputTypeAl'] == 'list':
            formData['highlight'] = True
        
        if "articlesets" not in formData:
            artsets = [str(aset.id) for aset in Project.objects.get(id=formData['projects']).all_articlesets()]
            formData.setlist("articlesets", artsets)


        if isinstance(self.data['projects'], (basestring, int)):
            project_id = int(self.data['projects'])
        else:
            project_id = int(self.data['projects'][0])

        
        if self.options['outputTypeAl'] == 'table':
            t = keywordsearch.getDatatable(self.data)
            t = t.rowlink_reverse("project-article-details", args=[project_id, '{id}'])
            cols = {FORM_FIELDS_TO_ELASTIC.get(f,f) for f in self.data.getlist('columns')}
            for f in list(t.get_fields()):
                if f not in cols:
                    t = t.hide(f)

            for col in cols & {'hits', 'text', 'lead'}:
                t = t.add_arguments(col=col)
            html = unicode(t)
            #html += "Download results as : "
            if self.output == "html":
                from django.http import HttpResponse
                response = HttpResponse(mimetype='text/html')
                response.write(html)
                return response
            else:
                return self.outputJsonHtml(html)
        else:
            n = keywordsearch.get_total_n(formData)
            articles = list(ArticleListScript(formData).run())
            for a in articles:
                a.hack_project_id = project_id
            self.output_template = 'api/webscripts/articlelist.html'
            
            return self.outputResponse(dict(articlelist=articles, n=n, page=formData.get('start')), ArticleListScript.output_type)
        
