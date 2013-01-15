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

"""
Script that stores matching articles as set
"""


from amcat.scripts import script, types
import amcat.scripts.forms
from django import forms
from amcat.models.article import Article
from amcat.models.project import Project
from amcat.models.articleset import ArticleSet

import logging
log = logging.getLogger(__name__)

class SaveAsSetForm(forms.Form):
    setname = forms.CharField(required=False)
    setproject = forms.ModelChoiceField(queryset=Project.objects.all(), required=False) # TODO: change to projects of user
    existingset = forms.ModelChoiceField(queryset=ArticleSet.objects.all(), required=False) #TODO: change to articlesets inside project

    def __init__(self, *args, **kwargs):
        super(SaveAsSetForm, self).__init__(*args, **kwargs)

        # Due to the design of (web)scripts, it is not possible to access
        # POST data below. A workaround is used below (navigator stores
        # a request object in the threads local storage) to access it, but
        # should be removed as soon as possible. 
        try:
            from navigator.utils.auth import get_request
            request = get_request()
        except ImportError:
            log.debug("AmCAT Navigator not installed! Wil not set default project / filter on existing sets.")
            return

        if request is None:
            log.debug("AmCAT Navigator not running! Wil not set default project / filter on existing sets.")
            return

        # Try to find out if we're on the Article Selection page
        project_id = request.REQUEST.get("project")

        if project_id is None:
            log.debug("Not on Article Selection page. Can't filter on existing set / default project.")
            return

        project = Project.objects.get(id=project_id)

        self.fields['setproject'].widget = forms.HiddenInput()
        self.fields['setproject'].initial = project
        self.fields['existingset'].queryset = ArticleSet.objects.filter(project=project)

    
    def clean(self):
        cleanedData = self.cleaned_data
        if cleanedData['existingset']:
            if 'setproject' in cleanedData: del cleanedData['setproject']
            if 'setname' in cleanedData: del cleanedData['setname']
        else:
            if not cleanedData.get('setname'):
                self._errors["setname"] = self.error_class(["Missing Set Name"])
            if not cleanedData.get('setproject'):
                self._errors["setproject"] = self.error_class(["Missing Project"])
        return cleanedData
        

class SaveAsSetScript(script.Script):
    input_type = types.ArticleidList
    options_form = SaveAsSetForm
    output_type = ArticleSet


    def run(self, articleids):
        if self.options['existingset']:
            s = self.options['existingset']
        else:
            name = self.options['setname']
            project = self.options['setproject']

            try:
                ArticleSet.objects.get(name=name, project=project)
            except ArticleSet.DoesNotExist:
                s = ArticleSet(name=self.options['setname'], project=self.options['setproject'])
                s.save()
            else:
                raise ValueError("Set with this name already exists!")

        s.add(*articleids)
        return s
    
        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(SaveAsSetScript)
