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

from django.conf.urls import include, patterns, url
from django.views.generic import RedirectView
from django.contrib import admin
from django.conf import settings

from os.path import abspath, dirname, join
import os; from os.path import isdir

import logging; log = logging.getLogger(__name__)

from navigator.utils.error_handlers import handler404, handler500, handler403

admin.autodiscover() 

urlpatterns = patterns(
    '',
    ('^$', RedirectView.as_view(url='navigator')),
    (r'^admin/', include(admin.site.urls)),
    (r'^accounts/', include('accounts.urls')),
    (r'^navigator/', include('navigator.urls')),
    (r'^api/', include('api.urls')),
    (r'^annotator/', include('annotator.urls')),
    url(r'^restframework', include('rest_framework.urls', namespace='rest_framework'))
    )

# Sentry
if settings.DEBUG == False and not settings.DISABLE_SENTRY:
    urlpatterns += patterns('', (r'^sentry/', include('sentry.web.urls')))

# Static files
if settings.LOCAL_DEVELOPMENT:
    urlpatterns += patterns("django.views",
        url(r"%s(?P<path>.*)$" % settings.MEDIA_URL[1:], "static.serve", {
            "document_root": settings.MEDIA_ROOT,
        })
    )
