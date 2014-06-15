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
import json
from amcat.models import Task
from amcat.tools.classtools import get_qualified_name
from amcat.tools.djangotoolkit import from_querydict

from api import webscripts
from api.webscripts.webscript import showErrorMsg
from django.http import HttpResponse

from amcat.forms import InvalidFormException
from amcat.models.project import Project

from navigator.views.scriptview import ScriptHandler

import logging
log = logging.getLogger(__name__)


class WebScriptHandler(ScriptHandler):
    def get_script(self):
        return self.task.get_class()(**self.get_form_kwargs())

    def run_task(self):
        response = super(WebScriptHandler, self).run_task()
        result = {"content": response.content,
                  "status": response.status_code,
                  "headers": response.items()}
        return result

    def get_response(self):
        raw = self.task._get_raw_result()
        result = HttpResponse(raw['content'], status=raw['status'])
        for header, val in raw['headers']:
            result[header] = val
        return result



def index(request, webscriptName):
    if not hasattr(webscripts, webscriptName) or webscriptName not in webscripts.webscriptNames:
        return showErrorMsg('invalid webscript name', 'json')
    webscriptClass = getattr(webscripts, webscriptName)


    project = Project.objects.only("id").get(id=request.GET["project"])
    user = request.user

    data = (request.POST if request.method == "POST" else request.GET).copy()
    data['projects'] = project.id

    try:
        try:
            called_with = dict(user=user.id, project=project.id, data=from_querydict(data))
            ws = webscriptClass(**called_with)
        except TypeError:
            called_with = dict(data=from_querydict(data))
            ws = webscriptClass(**called_with)
        # HACK: put query in session to allow highlighting
        request.session['query'] = data.get('query')

        if "delay" in request.GET:
            h = WebScriptHandler.call(target_class=ws.__class__, arguments=called_with, project=project, user=user)
            return HttpResponse(json.dumps({"task_uuid" : h.task.uuid}), content_type="application/json")
        else:
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
