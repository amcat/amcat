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
from django.conf.urls import include, patterns, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    '',
    (r'^admin/', include(admin.site.urls)),
    (r'^accounts/', include('accounts.urls')),
    (r'^', include('navigator.urls', namespace="navigator")),
    (r'^api/', include('api.urls', namespace="api")),
    (r'^', include('annotator.urls', namespace="annotator")),
    url(r'^restframework', include('rest_framework.urls', namespace='rest_framework'))
    )

# Static files (will be filtered by nginx on deployment)
urlpatterns += patterns("django.views",
    url(r"%s(?P<path>.*)$" % settings.MEDIA_URL[1:], "static.serve", {
        "document_root": settings.MEDIA_ROOT,
    })
)
