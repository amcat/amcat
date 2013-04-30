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
from amcat.tools import classtools
from navigator.utils.action import ActionHandler
from navigator.utils.auth import check
from api.rest import Datatable

from api.rest.resources import PluginResource

def get_menu():
    return tuple((pt.label, "manage-plugins", pt.id) for pt in PluginType.objects.all())

def index(request):
    menu = get_menu()
    types = PluginType.objects.all()
    return render(request, 'navigator/plugin/index.html', locals())
