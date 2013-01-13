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

from django.conf.urls import patterns, url, include

import api.rest

urlpatterns = patterns('',
    url(r'^$', 'api.views.index', name="api"),

    url(r'^action/(?P<action>\w+)$', 'api.action.handler'),

    (r'^webscript/(?P<webscriptName>\w+)/run$', 'api.webscripts.handler.index'),
    (r'^webscript/(?P<webscriptName>\w+)/form$', 'api.webscripts.handler.getWebscriptForm'),
    (r'^v4/', include('api.rest.urls')),
    url(r'^restframework', include('rest_framework.urls', namespace='rest_framework')),

)

