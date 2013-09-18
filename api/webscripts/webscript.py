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


from django.template.loader import render_to_string
import time
import api.webscripts
from django.db import connection
from django.utils import simplejson
from amcat.scripts import scriptmanager, types
from django.http import HttpResponse
from amcat.scripts.forms import SelectionForm
from amcat.forms import InvalidFormException

import logging
log = logging.getLogger(__name__)


mimetypeDict = { #todo: make objects of these
    'json':{'extension':'json', 'mime':'text/plain', 'download':False},
    'csv':{'extension':'csv', 'mime':'text/csv', 'download':True},
    'comma-csv':{'extension':'csv', 'mime':'text/csv', 'download':True},
    'excel':{'extension':'xlsx', 'mime':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'download':True},
     'html':{'extension':'html', 'mime':'text/html', 'download':False},
     'spss':{'extension':'sav', 'mime':'application/octet-stream', 'download':True},
     'datatables':{'extension':'json', 'mime':'text/plain', 'download':False},
}


class WebScript(object):
    """
    A WebScript is a combination of Scripts, with no input and a Django HttpResponse as output
    """
    name = None # the name of this webscript
    form_template = None # special markup to display the form, filename
    form = None # fields specific for this webscript
    displayLocation = None # should be (a list of) another WebScript name that is displayed in the main form
    id = None # id used in webforms
    output_template = None # path to template used for html output
    solrOnly = False # only for Solr output, not on database queries

    def __init__(self, project=None, data=None, **kwargs):
        self.initTime = time.time()
        self.data = data
        self.output = data.get('output', 'json')
        self.project = project

        if self.form:

            try:
                form = self.form(project=project, data=data, **kwargs)
            except TypeError:
                form = self.form(data=data, **kwargs)

            if not form.is_valid():
                raise InvalidFormException("Invalid or missing options: %r" % form.errors, form.errors)
            self.options = form.cleaned_data
            self.formInstance = form
        else:
            self.options = None
            self.formInstance = None

    @classmethod
    def formHtml(cls, project=None):
        if cls.form == None:
            return ''
        try:
            form = cls.form(project=project)
        except TypeError:
            form = cls.form()
        return render_to_string(cls.form_template, {'form':form}) if cls.form_template else form.as_p()


    def getActions(self):
        for ws in api.webscripts.actionScripts:
            if self.__class__.__name__ in ws.displayLocation and (ws.solrOnly == False or self.data.get('query')):
                yield ws.__name__, ws.name 


    def outputJsonHtml(self, scriptoutput):
        actions = self.getActions()

        webscriptform = None
        if self.form:
            try:
                webscriptform = self.form(project=self.project, data=self.data)
            except TypeError:
                webscriptform = self.form(data=self.data)

        selectionform = SelectionForm(project=self.project, data=self.data)
        html = render_to_string('navigator/selection/webscriptoutput.html', {
                                    'scriptoutput':scriptoutput,
                                    'actions': actions,
                                    'selectionform':selectionform,
                                    'webscriptform':webscriptform
                               })
        reply = {}
        reply['html'] = html
        reply['queries'] = getQueries()
        reply['querytime'] = '%.2f' % (time.time() - self.initTime)
        reply['webscriptName'] = self.name
        reply['webscriptClassname'] = self.__class__.__name__
        jsondata = simplejson.dumps(reply, default=lambda o:unicode(o))
        return HttpResponse(jsondata, mimetype='text/plain')

    def outputResponse(self, data, data_type, filename=None):
        outputFormData = self.data.copy() # need copy, else it's unmutable
        outputFormData['template'] = self.output_template
        if self.output == 'json-html': # special output that runs the webscript with html output,
                                       # then wraps around this the action buttons and other stuff for the amcat navigator website
            if data_type == unicode:
                scriptoutput = data
            else:
                cls = scriptmanager.findScript(data_type, 'html')
                if not cls: raise Exception('html output not supported')
                scriptoutput = cls(outputFormData).run(data)
            return self.outputJsonHtml(scriptoutput)
        else:
            cls = scriptmanager.findScript(data_type, self.output)
            if not cls: raise Exception('invalid output type')
            #cnf = {'template':self.output_template} if self.output == 'html' else None
            mimetype = mimetypeDict[self.output]
            out = cls(outputFormData).run(data)

            response = HttpResponse(mimetype=mimetype['mime'])
            response.write(out)
            if filename or mimetype['download'] == True:
                if not filename:
                    filename = 'AmCAT %s' % self.name
                response['Content-Disposition'] = 'attachment; filename="%s.%s"' % (filename, mimetype['extension'])
            return response


def getQueries():
    return [(x.get('time') or x.get('duration'), x['sql']) for x in connection.queries]

def showErrorMsg(text, outputType, fields=None):
    errormsg = types.ErrorMsg(text, fields=fields)
    cls = scriptmanager.findScript(types.ErrorMsg, outputType)
    output = cls().run(errormsg) if cls else text
    return HttpResponse(output, mimetype='text/plain')
