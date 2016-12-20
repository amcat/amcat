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

import json
import logging

from amcat.scripts.query.queryaction import is_valid_cache_key
from django import conf
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models.query_utils import Q
from django.http import HttpResponseBadRequest, HttpResponse
from django.views.generic.base import TemplateView, RedirectView, View

from amcat.models import Query
from amcat.scripts.forms import SelectionForm
from amcat.tools import amcates
from api.rest.datatable import Datatable
from api.rest.viewsets import QueryViewSet, FavouriteArticleSetViewSet, CodingJobViewSet
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin

log = logging.getLogger(__name__)

SHOW_N_RECENT_QUERIES = 5

class ClearQueryCacheView(ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, View):
    context_category = 'Query'
    parent = ProjectDetailsView
    url_fragment = 'clear-query-cache'
    view_name = 'clear-query-cache'

    http_method_names = ["post"]

    def post(self, *args, **kwargs):
        cache_key = self.request.POST.get("cache-key")

        if not is_valid_cache_key(cache_key):
            return HttpResponseBadRequest("Invalid cache key.")

        cache.set(cache_key, None)
        return HttpResponse("OK")

class SavedQueryRedirectView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, RedirectView):
    model = Query
    parent = ProjectDetailsView
    url_fragment = 'query/(?P<query>[0-9]+)'
    view_name = 'saved_query'
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        query_id = int(self.kwargs["query"])
        query = Query.objects.get(id=query_id)
        script_name = query.parameters["script"]
        sets = ",".join(map(str, query.get_articleset_ids()))
        codingjobs = ",".join(map(str, query.get_codingjob_ids()))
        url = reverse("navigator:query", args=[self.project.id])

        if codingjobs:
            url += "?query={query_id}&jobs={codingjobs}#{script_name}".format(**locals())
        else:
            url += "?query={query_id}&sets={sets}#{script_name}".format(**locals())

        return url


class QueryView(ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, TemplateView):
    context_category = 'Query'
    parent = ProjectDetailsView
    url_fragment = 'query'
    view_name = 'query'

    def get_saved_queries_table(self):
        table = Datatable(
            QueryViewSet,
            url_kwargs={"project": self.project.id},
            rowlink="{id}"
        )
        table = table.hide("last_saved", "parameters", "project")
        return table

    def get_articlesets_table(self):
        table = Datatable(
            FavouriteArticleSetViewSet,
            url_kwargs={"project": self.project.id},
            rowlink="?sets={id}",
            checkboxes=True
        )

        table = table.hide("favourite", "featured", "project", "provenance")
        return table

    def get_codingjobs_table(self):
        table = Datatable(
            CodingJobViewSet,
            url_kwargs={"project": self.project.id},
            rowlink="?jobs={id}",
            checkboxes=True
        ).filter(archived=False).hide("articleset", "archived", "insertuser")
        return table

    def _get_ids(self, key):
        return set(map(int, filter(str.isdigit, self.request.GET.get(key, "").split(","))))

    def get_context_data(self, **kwargs):
        query_id = self.request.GET.get("query", "null")
        user_id = self.request.user.id

        article_ids = self._get_ids("articles")
        article_ids_lines = "\n".join(str(id) for id in article_ids)
        articleset_ids = self._get_ids("sets")
        codingjob_ids = self._get_ids("jobs")
        codingjob_ids_json = json.dumps(list(codingjob_ids))

        if codingjob_ids:
            all_articlesets = self.project.favourite_articlesets.all().only("id", "name")
            all_articlesets = all_articlesets.filter(codingjob_set__id__in=codingjob_ids)
            articleset_ids = all_articlesets.values_list("id", flat=True)
            all_codingjobs = self.project.codingjob_set.all().filter(id__in=codingjob_ids)
        else:
            all_codingjobs = None
            all_articlesets = self.project.favourite_articlesets.all().only("id", "name")
            all_articlesets = all_articlesets.filter(codingjob_set__id__isnull=True)

        articlesets = self.project.all_articlesets().filter(id__in=articleset_ids).only("id", "name")
        articlesets_names = (aset.name for aset in articlesets)
        articleset_ids_json = json.dumps(list(articleset_ids))
        codebooks = self.project.get_codebooks().order_by("name").only("id", "name")

        saved_queries_table = self.get_saved_queries_table()
        articlesets_table = self.get_articlesets_table()
        codingjobs_table = self.get_codingjobs_table()

        form = SelectionForm(
            project=self.project,
            articlesets=articlesets,
            codingjobs=all_codingjobs,
            data=self.request.GET,
            initial={
                "datetype": "all",
                "articlesets": articlesets
            }
        )

        statistics = amcates.ES().statistics(filters={"sets": list(articleset_ids)})
        settings = conf.settings

        saved_queries = Query.objects.filter(project=self.project)

        if self.request.user.is_anonymous():
            saved_user_queries, saved_project_queries = [], saved_queries
        else:
            saved_user_queries = saved_queries.filter(user=self.request.user)[:SHOW_N_RECENT_QUERIES]
            saved_project_queries = saved_queries.filter(~Q(user=self.request.user))[:SHOW_N_RECENT_QUERIES]

        form.fields["articlesets"].widget.attrs['disabled'] = 'disabled'
        return dict(super(QueryView, self).get_context_data(), **locals())

