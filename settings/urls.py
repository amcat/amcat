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
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.static import serve

from navigator.utils.error_handlers import *

admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^', include('navigator.urls', namespace="navigator")),
    url(r'^api/', include('api.urls', namespace="api")),
    url(r'^', include('annotator.urls', namespace="annotator")),
    url(r'^restframework', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]

# Static files (will be filtered by nginx on deployment)
urlpatterns += [
    url(r"%s(?P<path>.*)$" % settings.MEDIA_URL[1:], serve, {
        "document_root": settings.MEDIA_ROOT,
    })
]
