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
from amcat.tools.selection.webscripts.webscript import WebScript
from amcat.model.project import Project

    
class SaveAsSetForm(forms.Form):
    setname = forms.CharField()
    project =  forms.ModelChoiceField(queryset=Project.objects.all()) # TODO: change to projects of user

class SaveAsSet(WebScript):
    name = "Save as set"
    template = None
    form = SaveAsSetForm
    displayLocation = 'ShowTable'
    
    def run(self):
        pass