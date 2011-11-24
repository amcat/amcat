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
Script that will run a search on the database or Solr and return the matching Article objects
"""


from amcat.scripts import script, types
from amcat.scripts.tools import cli
import amcat.scripts.forms
from django import forms
from amcat.model.project import Project
import amcat.model
import amcat.scripts.forms

import logging
log = logging.getLogger(__name__)





    
class ViewModelForm(amcat.scripts.forms.GeneralColumnsForm):
    start = forms.IntegerField(initial=0, min_value=0, widget=forms.HiddenInput, required=False)
    length = forms.IntegerField(initial=100, min_value=1, max_value=9999999, widget=forms.HiddenInput, required=False)
    model = forms.CharField()
    search = forms.CharField(required=False)
    projects = forms.ModelMultipleChoiceField(queryset=Project.objects.all(), required=False) # TODO: change to projects of user
    
    sortColumnNr = forms.IntegerField(required=False)
    sortOrder = forms.ChoiceField(
                    choices=(
                        ('asc', 'Ascending'), 
                        ('desc', 'Descending'),
                     ),
                    initial = 'asc', required=False)
    
    
    
    def clean_start(self):
        data = self.cleaned_data['start']
        if data == None:
            data = 0
        return data
        
    def clean_length(self):
        data = self.cleaned_data['length']
        if data == None:
            data = 100
        if data == -1:
            data = 999999 # unlimited (well, sort of ;)
        return data
        
    def clean_model(self):
        data = self.cleaned_data['model']
        
        if '.' in data:
            split = data.split('.')
            clss = getattr(amcat.model, split[0])
            moduleobj = getattr(clss, split[1].lower())
            data = split[1]
        else:
            moduleobj = getattr(amcat.model, data.lower())
        data = getattr(moduleobj, data)
        # if not hasattr(amcat.model, data.lower()):
            # self._errors["modelname"] = self.error_class(['Invalid model name'])
            # return None
        return data
        
        

class FindObjectsScript(script.Script):
    input_type = None
    options_form = ViewModelForm
    output_type = types.ObjectIterator


    def run(self, input=None):
        """ returns an iterable of model objects """
        start = self.options['start']
        length = self.options['length']
        
        kargs = {}
        if self.options['projects']:
            if self.options['model'].__name__ != 'Project':
                kargs['project__in'] = self.options['projects']
        qs = self.options['model'].objects.filter(**kargs)
        if self.options['sortColumnNr']:
            column = self.options['columns'][self.options['sortColumnNr']]
            qs = qs.order_by(('-' if self.options['sortOrder'] == 'desc' else '') + column)
            
            
        #TODO: implement search
            
        qs = qs[start:start+length]
        return qs

        
        
if __name__ == '__main__':
    cli.run_cli(FindObjectsScript)