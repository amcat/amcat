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
from functools import partial
from itertools import chain
from operator import getitem, attrgetter
from collections import OrderedDict
from django.core.exceptions import ValidationError
from django.db.models import Q

from rest_framework.exceptions import APIException
from rest_framework.metadata import SimpleMetadata
from rest_framework.response import Response
from rest_framework.views import APIView

from amcat.models import Project, CodingJob, ArticleSet
from amcat.tools.amcates import ES, get_property_mapping_type
from amcat.tools.caching import cached


def wrap_query_action(qaction):
    class AutoQueryActionViewSet(QueryActionView):
        help_text = qaction.__doc__
        query_action = qaction
    return AutoQueryActionViewSet


class QueryActionMetadata(SimpleMetadata):
    bucket_count_limit = 500

    def determine_metadata(self, request, view):
        form = view.get_form()
        field_names = list(form.fields.keys())
        fields = list(map(partial(getitem, form), field_names))

        articlesets = view.get_articlesets()

        props = {prop for aset in articlesets for prop in aset.get_used_properties()}
        articleset_ids = list(articlesets.values_list('id', flat=True))

        # lucene limitation
        setsquery = {
           'bool': {
                'should': [ {'terms': {'sets': articleset_ids[i:i+1000]} } for i in range(0, len(articleset_ids), 1000) ]
            }
        }

        aggs = ES().search({
            'aggs': {
                k: {
                    'terms': {
                        'field': '{}.raw'.format(k) if get_property_mapping_type(k) == "default" else k,
                        'size': self.bucket_count_limit
                    }
                } for k in props
            },
            'query': setsquery
        })['aggregations']

        filter_props = {k: [v['key'] for v in vs['buckets']] for k, vs in aggs.items()}

        return {
            "help_texts": OrderedDict(zip(field_names, [f.help_text.strip() or None for f in fields])),
            "form": OrderedDict(zip(field_names, [f.as_widget() for f in fields])),
            "labels": OrderedDict(zip(field_names, [f.label for f in fields])),
            "help_text": view.get_view_description(),
            "filter_properties": filter_props  # TODO: filter_properties should be moved to a different view.
        }


class QueryActionView(APIView):
    query_action = None
    metadata_class = QueryActionMetadata
    #http_method_names = "POST", "OPTIONS"

    def __init__(self, **kwargs):
        super(QueryActionView, self).__init__(**kwargs)

    @property
    def project(self):
        return self.get_project()

    @property
    def articlesets(self):
        return self.get_articlesets()

    @property
    def codingjobs(self):
        return self.get_codingjobs()

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
        # TODO: GET['sets'] and POST['articlesets'] are redundant, possibly there's a better solution
        articleset_ids = chain(
            getattr(self.request, "OPTIONS", {}).get("sets", "").split(","),
            self.request.GET.get("sets", "").split(","),
            self.request.POST.getlist('articlesets')
        )

        articleset_ids = map(int, filter(str.isdigit, articleset_ids))

        articlesets = self.project.all_articlesets()
        if self.get_codingjobs().exists():
            articlesets = self.project.all_articlesets_and_coding_sets()

        articlesets = articlesets.filter(id__in=articleset_ids)
        return articlesets.only("id", "name")

    @cached
    def get_codingjobs(self):
        # Codingjobs are given by GET parameter `jobs` and separated by commas. If *no* jobs are
        # given, we also return no jobs, in contrast to get_articlesets which yields all articlesets
        # belonging to the current project.
        codingjob_ids = chain(
            getattr(self.request, "OPTIONS", {}).get("jobs", "").split(","),
            self.request.GET.get("jobs", "").split(","),
            self.request.POST.getlist('codingjobs')
        )

        codingjob_ids = map(int, filter(str.isdigit, codingjob_ids))
        codingjobs = CodingJob.objects.filter(Q(project=self.project) | Q(linked_projects=self.project))
        codingjobs = codingjobs.filter(id__in=codingjob_ids)
        return codingjobs if codingjob_ids else CodingJob.objects.none()

    @cached
    def get_query_action(self):
        host = "{protocol}://{host}/".format(protocol=("https" if self.request.is_secure() else "http"),
                                             host=self.request.get_host())
        return self.query_action(
            user=self.request.user, project=self.get_project(), codingjobs=self.get_codingjobs(),
            articlesets=self.get_articlesets(), data=self.request.POST or self.request.data or None,api_host=host
        )

    def get_form(self):
        return self.get_query_action().get_form()

    def get_view_name(self):
        from .urls import get_action_name
        return get_action_name(self).title()

    def get_view_description(self, html=False):
        return (self.query_action.__doc__ or "").strip()

    def dispatch(self, request, *args, **kwargs):
        return super(QueryActionView, self).dispatch(request, *args, **kwargs)

    def get(self, request, format=None):
        return Response({"details": "POST/OPTIONS only."})

    def post(self, request, format=None):
        try:
            qa = self.get_query_action()

            #HACK! Sets query to session for article higlighting
            request.session['query'] = qa.data['query']

            task_handler = qa.run_delayed()
        except ValidationError as e:
            return Response(e.message_dict, status=400)
        else:
            return Response({"uuid": task_handler.task.uuid})

