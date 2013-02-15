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

from api import webscripts
from api.webscripts.webscript import showErrorMsg
from django.http import HttpResponse

from amcat.forms import InvalidFormException
from amcat.models.project import Project

import logging
log = logging.getLogger(__name__)

def index(request, webscriptName):
    if not hasattr(webscripts, webscriptName) or webscriptName not in webscripts.webscriptNames:
        return showErrorMsg('invalid webscript name', 'json')
    webscriptClass = getattr(webscripts, webscriptName)
    try:
        ws = webscriptClass(request.POST if request.method == "POST" else request.GET)
        return ws.run()
    except InvalidFormException, e:
        log.exception('Invalid form for Webscript: %s' % webscriptName)
        return showErrorMsg('Invalid form', 'json', fields=e.getErrorDict())
    except Exception, e:
        log.exception('Webscript exception: %s' % webscriptName)

        if hasattr(e, 'reason') and e.reason == 'null':
            e.reason = 'This query could not be parsed.'

        return showErrorMsg('error running webscript: %s' % e, 'json')
        
    
    
def getWebscriptForm(request, webscriptName):
    if not hasattr(webscripts, webscriptName) or webscriptName not in webscripts.webscriptNames:
        return showErrorMsg('invalid webscript name', 'json')
    webscriptClass = getattr(webscripts, webscriptName)

    project = None
    if 'project' in request.GET:
        project = Project.objects.get(id=request.GET.get('project'))

    return HttpResponse(webscriptClass.formHtml(project))
    
    
def model(request, modelName):
    data = request.POST if request.method == "POST" else request.GET
    data = data.copy()
    data['model'] = modelName
    try:
        return webscripts.viewmodel.ViewModel(data).run()
    except InvalidFormException, e:
        log.exception('model webscript exception')
        return showErrorMsg('Invalid form', 'json', fields=e.getErrorDict())
    except Exception, e:
        log.exception('model webscript exception')
        return showErrorMsg('error running webscript: %s' % e, 'json')
    
