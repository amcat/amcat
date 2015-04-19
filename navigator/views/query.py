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
import json
from django.core.urlresolvers import reverse
from django.db.models.query_utils import Q
from django.http import HttpResponseBadRequest, Http404, HttpResponseRedirect
from django.shortcuts import redirect

from django.views.generic.base import TemplateView
from amcat.models import Query
from amcat.tools.amcates import ES

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin
from amcat.scripts.forms import SelectionForm
from navigator.views.project_views import ProjectDetailsView

SHOW_N_QUERIES = 5


class QueryView(ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, TemplateView):
    context_category = 'Query'
    parent = ProjectDetailsView
    url_fragment = 'query'
    view_name = 'query'

    def get(self, request, *args, **kwargs):
        """
        Return BadRequest if query id not a valid integer
        Return Http404 if query not found
        Return redirect if no sets given
        """
        query_id = self.request.GET.get("query")

        try:
            query_id = int(query_id)
        except ValueError:
            return HttpResponseBadRequest("{query_id} is not a valid integer".format(**locals()))
        except TypeError:
            pass
        else:
            owned_queries = Q(user__id=self.request.user.id)
            project_queries = Q(project__id=self.project.id, private=False)
            queries = Query.objects.filter(owned_queries | project_queries)

            query = queries.filter(id=query_id)
            if not query:
                raise Http404("Query {query_id} not found".format(**locals()))

            if "sets" not in self.request.GET:
                sets = ",".join(map(str, query[0].get_articleset_ids()))
                url = reverse("query", args=[self.project.id])
                url += "?query={query_id}&sets={sets}".format(**locals())
                return redirect(url)

        return super(QueryView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        articleset_ids = map(int, filter(unicode.isdigit, self.request.GET.get("sets", "").split(",")))
        articlesets = self.project.all_articlesets().filter(id__in=articleset_ids)
        articlesets = articlesets.only("id", "name")
        query_id = self.request.GET.get("query", "null")

        statistics = ES().statistics(query="*", filters={
            "sets": [aset.id for aset in articlesets]
        })

        form = SelectionForm(
            project=self.project,
            articlesets=articlesets,
            data=self.request.GET,
            initial={
                "datetype": "all",
                "articlesets": articlesets
            }
        )

        saved_queries = Query.objects.filter(project=self.project)
        saved_user_queries = saved_queries.filter(user=self.request.user)[:SHOW_N_QUERIES]
        saved_project_queries = saved_queries.filter(~Q(user=self.request.user))[:SHOW_N_QUERIES]

        form.fields["articlesets"].widget.attrs['disabled'] = 'disabled'
        return dict(super(QueryView, self).get_context_data(), **locals())
