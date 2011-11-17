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


from amcat.scripts import script
from amcat.scripts.tools import cli
import amcat.scripts.forms
from django import forms
from amcat.model.project import Project
from amcat.model.set import Set

import logging
log = logging.getLogger(__name__)

class SaveAsSetForm(forms.Form):
    setname = forms.CharField()
    project =  forms.ModelChoiceField(queryset=Project.objects.all()) # TODO: change to projects of user


class SaveAsSetScript(script.Script):
    input_type = script.ArticleidList
    options_form = SaveAsSetForm
    output_type = boolean


    def run(self, articleids):
        setname = self.options['setname']
        project = self.options['project']
        s = Set(name=setname, project=project)
        s.save()
        # TODO: add articles in bulk to set
        # s.articles.add(articles)
        return True
    
        
if __name__ == '__main__':
    cli.run_cli(SaveAsSetScript)