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


from amcat.scripts.searchscripts.findobjects import FindObjectsScript
from amcat.scripts.processors.objects_to_table import ObjectsToTable

import logging
log = logging.getLogger(__name__)


class ViewModelForm(forms.Form):
    pass
    #modelname = forms.CharField()
    
    
class ViewModel(WebScript):
    name = "View Model"
    form = ViewModelForm
    displayLocation = ()
    
    
    def run(self):
        objects = FindObjectsScript(self.formData).run()
        result = ObjectsToTable(self.formData).run(objects)

        return self.outputResponse(result, ObjectsToTable.output_type)
        
    