##########################################################################
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
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.routers import DefaultRouter

from api.rest import resources
from api.rest.viewsets import get_viewsets

router = DefaultRouter()
for vs in get_viewsets():
    router.register(vs.get_url_pattern(), vs, base_name=vs.get_basename())

urlpatterns = format_suffix_patterns(patterns('',
    url(r'^$', resources.api_root),
    url(r'^taskresult/(?P<task_id>[0-9]+)$', resources.single_task_result, dict(uuid=False)),
    url(r'^taskresult/(?P<task_id>[0-9a-zA-Z-]+)$', resources.single_task_result, dict(uuid=True)),
    url(r'^get_token', 'api.rest.get_token.obtain_auth_token'),

    *tuple(r.get_url_pattern() for r in resources.all_resources())
))

urlpatterns +=  patterns('',
    url(r'^', include(router.urls)),
)
