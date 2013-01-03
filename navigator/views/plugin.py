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
Controller for pages related to plugin management
"""

import logging; log = logging.getLogger(__name__)


from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django import forms

from amcat.models.plugin import Plugin, PluginType
from amcat.scripts.actions.add_plugin import AddPlugin
from amcat.tools import classtools
from navigator.utils.action import ActionHandler
from navigator.utils.auth import check
from api.rest import Datatable

#from api.rest.analysis import AnalysisResource, PluginResource

def get_menu():
    return tuple((pt.label, "manage-plugins", pt.id) for pt in PluginType.objects.all())

def index(request):
    menu = get_menu()
    types = PluginType.objects.all()
    return render(request, 'navigator/plugin/index.html', locals())

@check(PluginType)
def manage(request, plugin_type):
    menu = get_menu()
    selected = plugin_type.label
    canmanage = Plugin.can_create(request.user)
    if plugin_type.label == 'NLP Preprocessing':
        resource = AnalysisResource
        rowlink = "../analysis/{id}"
    else:
        resource = PluginResource
        rowlink = None
    plugins = (Datatable(resource, rowlink=rowlink)
               .filter(type=plugin_type).hide('id', 'type'))
    return render(request, 'navigator/plugin/manage.html', locals())

@check(PluginType)
def add(request, plugin_type):
    if request.POST:
        form = AddPlugin.options_form(request.POST)
        if form.is_valid():
            added_plugin = AddPlugin(form).run()
            return redirect(reverse(manage, args=[plugin_type.id]), permanent=False)
    else:
        form = AddPlugin.get_empty_form(type=plugin_type)

    scripts = plugin_type.get_classes()
    c = forms.ChoiceField(choices=[(0, "---")] +
                          [("%s.%s" % (c.__module__, c.__name__), c.__name__)
                           for c in scripts],
                          initial=0)
    form.fields.insert(0, "Known plug-in", c)
    return render(request, "navigator/plugin/add.html", locals())
