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
from __future__ import unicode_literals
from functools import partial
from operator import getitem

from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from amcat.models import Project
from amcat.tools.caching import cached


def wrap_query_action(qaction):
    class AutoQueryActionViewSet(QueryActionView):
        help_text = qaction.__doc__
        query_action = qaction
    return AutoQueryActionViewSet


class QueryActionView(APIView):
    query_action = None

    def __init__(self, **kwargs):
        super(QueryActionView, self).__init__(**kwargs)

    @property
    def project(self):
        return self.get_project()

    @property
    def articlesets(self):
        return self.get_articlesets()

    @cached
    def get_project(self):
        try:
            return Project.objects.get(id=int(self.request.GET["project"]))
        except KeyError:
            raise APIException({"details": "You need to provide 'project' GET parameter."})
        except ValueError:
            raise APIException({"details": "You need to specify an integer as project id."})
        except Project.DoesNotExist:
            raise APIException({"details": "Project does not exist."})

    @cached
    def get_articlesets(self):
        # Articlesets are given by GET parameter `sets` and separated by commas
        articleset_ids = map(int, filter(unicode.isdigit, self.request.GET.get("sets", "").split(",")))
        articlesets = self.project.all_articlesets().filter(id__in=articleset_ids)
        return articlesets.only("id", "name")

    @cached
    def get_query_action(self):
        return self.query_action(
            user=self.request.user, project=self.get_project(),
            articlesets=self.get_articlesets(), data=self.request.POST or None
        )

    def get_form(self):
        return self.get_query_action().get_form()

    def get_view_name(self):
        from urls import get_action_name
        return get_action_name(self).title()

    def get_view_description(self, html=False):
        return self.query_action.__doc__.strip()

    def dispatch(self, request, *args, **kwargs):
        return super(QueryActionView, self).dispatch(request, *args, **kwargs)

    def get(self, request, format=None):
        return Response({"details": "POST/OPTIONS only."})

    def post(self, request, format=None):
        task_handler = self.get_query_action().run_delayed()
        return Response({"uuid": task_handler.task.uuid})

    def metadata(self, request):
        field_names = self.get_form().fields.keys()
        fields = map(partial(getitem, self.get_form()), field_names)

        return {
            "help_text": self.get_view_description(),
            "form": dict(zip(field_names, map(unicode, fields)))
        }
