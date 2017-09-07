# #########################################################################
# (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
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
from inspect import isclass

from django.conf.urls import url
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from amcat.scripts.query import *
from api.rest.query.viewset import wrap_query_action


def get_action_name(viewcls):
    return viewcls.query_action.get_action_name()


def get_url_name(viewcls):
    """Returns urlname (used in urlpatterns) for this view."""
    return "queryaction-%s" % get_action_name(viewcls)

def is_query_action(cls):
    return isclass(cls) and issubclass(cls, QueryAction) and cls is not QueryAction

def get_query_actions():
    return filter(is_query_action, globals().values())

def get_url_pattern(viewcls):
    name = get_action_name(viewcls)

    return url(
        view=viewcls.as_view(),
        regex=r"^{name}$".format(**locals()),
        name="queryaction-{name}".format(**locals())
    )


def get_url_patterns():
    return [get_url_pattern(x) for x in get_query_action_viewsets()]


def get_query_action_viewsets():
    return map(wrap_query_action, get_query_actions())


class QueryActionIndex(APIView):
    def get(self, request):
        return Response({
            get_action_name(viewcls): reverse(get_url_name(viewcls), request=request)
            for viewcls in get_query_action_viewsets()
        })


urlpatterns = get_url_patterns() + [
    url(view=QueryActionIndex.as_view(), regex=r"^$", name="queryaction-index")
]
