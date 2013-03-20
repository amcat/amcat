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
Controller that handles calling plugin scripts as web services
"""

from django.shortcuts import render
from django.http import HttpResponse

import logging; log = logging.getLogger(__name__)

import simplejson
import traceback

from amcat.scripts.actions.get_codingjob_results import GetCodingJobResults
from amcat.scripts.actions.query import Query
from amcat.scripts.actions.get_queries import GetQueries
from amcat.scripts.script import Script
from amcat.scripts import scriptmanager

def get_script(action):
    for name, obj in globals().iteritems():
        if name == action and issubclass(obj, Script):
            return obj
    raise ValueError("Action {action} could not be found".format(**locals()))

def handler(request, action):
    script = get_script(action)
    result = None
    output = 'json'
    output = request.GET.get('format', 'json')
    if request.POST:
        form = script.options_form(request.POST)
        if form.is_valid():
            try:
                result = script(request.POST).run(None)
                converter = scriptmanager.findScript(script.output_type, output)
                if converter:
                    result = converter().run(result)
                    mimetype = 'text/csv'
                else:
                    result =simplejson.dumps(result)
                    mimetype = 'application/json'
                return HttpResponse(result, status=201, mimetype=mimetype)
            except Exception as e:
                error = {
                    'error-class' : e.__class__.__name__,
                    'error-message' : str(e),
                    'error-traceback' : traceback.format_exc()
                    }
                return HttpResponse(simplejson.dumps(error),
                                    mimetype='application/json', status=500)
        else:
            return HttpResponse(simplejson.dumps(form.errors),
                                mimetype='application/json', status=400)
            
    else:
        form = script.options_form
        status = 200
        return render(request, "api/action.html", locals())
