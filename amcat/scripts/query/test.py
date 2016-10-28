##########################################################################
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
from rpy2.robjects import r
from rpy2 import robjects
import os
import json
from django import forms
from django.core.exceptions import ValidationError
from amcat.scripts.query import QueryAction, QueryActionForm
from collections import OrderedDict
 
_R_INITIALIZED = False
def _initialize():
    global _R_INITIALIZED
    if _R_INITIALIZED:
        return 
    ## set path from which R loads packages and where R stores new packages (install can be called from within R plugins)
    pkgdir = os.path.join(os.path.dirname(__file__), 'r_plugins/package_library')
    if not os.path.exists(pkgdir):
        os.makedirs(pkgdir)
    r(".libPaths('{pkgdir}')".format(**locals()))
    source('r_plugins/formfield_functions.r', init=False)
    _R_INITIALIZED = True

def source(filename, init=True):
    if init:
        _initialize()
    filename = os.path.join(os.path.dirname(__file__), filename)
    r('source("{filename}")'.format(**locals()))
    
class RAction(QueryAction):
    output_types = (("text/html", "Result"),)
    
    @property
    def form_class(self):
        source(self.file)
        class DynamicForm(RForm):
            fieldinfo = json.loads(r('formfields')[0], object_pairs_hook=OrderedDict)
        return DynamicForm

    def run(self, form):
        def clean(x):
            from django.db.models import Model
            from django.db.models.query import QuerySet
            if isinstance(x, QuerySet):
                x = list(x)
            if isinstance(x, list):
                return [clean(y) for y in x]
            if isinstance(x, Model):
                return x.pk
            return x
        
        data = form.cleaned_data
        data = {k:clean(v) for (k,v) in data.items() if v}
        data = json.dumps(data, indent=4)
        res = robjects.StrVector([data])
        from rpy2.robjects.packages import importr
        rjson = importr("rjson")
        x = rjson.fromJSON(res)
        source(self.file)
        return str(r['do.call']('run', x))


class TestAction(RAction):
    output_types = (("text/html", "Result"),)
    file = "r_plugins/demo_plugin1.r"



class RForm(QueryActionForm):
    fieldinfo = None
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        for label, field in self.fieldinfo.items():
            fieldclass = getattr(forms, field['type'])
            self.fields[label] = fieldclass(**field['arguments'])
