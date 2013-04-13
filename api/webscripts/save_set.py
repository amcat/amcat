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
from django import forms
from amcat.scripts.searchscripts.articleids import ArticleidsScript
from amcat.scripts.processors.save_set import SaveAsSetScript, SaveAsSetForm


import logging
import json

log = logging.getLogger(__name__)

class SaveAsSetWebScriptForm(SaveAsSetForm):
    output = forms.CharField(widget=forms.HiddenInput(), initial='json-html')
    length = forms.IntegerField(widget=forms.HiddenInput(), initial=99999999)
    start = forms.IntegerField(widget=forms.HiddenInput(), initial=0)

    
class SaveAsSet(WebScript):
    name = "Save as Set"
    form_template = None#"api/webscripts/save_set_form.html"
    form = SaveAsSetWebScriptForm
    displayLocation = ('ShowSummary', 'ShowArticleList')
    output_template = "api/webscripts/save_set.html" 
    
    
    def run(self):
        articleids = ArticleidsScript(self.formData).run()
        result = SaveAsSetScript(self.formData).run(articleids)
        result.provenance = json.dumps(dict(self.formData))
        result.save()

        return self.outputResponse(result, object)
        
    
