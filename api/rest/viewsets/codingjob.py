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
from django.db.models import Count
from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet
from amcat.models import CodingJob
from amcat.models.coding import coding
from amcat.tools.caching import cached
from api.rest.resources.amcatresource import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewsets.project import ProjectViewSetMixin

STATUS_DONE = (coding.STATUS_COMPLETE, coding.STATUS_IRRELEVANT)

__all__ = ("CodingJobViewSetMixin", "CodingJobSerializer", "CodingJobViewSet")


class CodingJobSerializer(AmCATModelSerializer):
    """
    This serializer for codingjob includes the amount of total jobs
    and done jobs. Because it would be wholly inefficient to calculate
    the values per codingjob, we ask the database to aggregate for us
    in one query.
    """
    n_articles = serializers.SerializerMethodField('get_n_articles')
    n_codings_done = serializers.SerializerMethodField('get_n_done_jobs')

    def _get_codingjobs(self):
        view = self.context["view"]
        if hasattr(view, "object_list"):
            return view.object_list.distinct()
        return CodingJob.objects.filter(id=view.object.id)

    @cached
    def _get_n_done_jobs(self):
        return dict(self._get_codingjobs().filter(
                    codings__status__in=STATUS_DONE).annotate(Count("codings"))
                    .values_list("id", "codings__count"))

    @cached
    def _get_n_articles(self):
        return dict(self._get_codingjobs().annotate(n=Count("articleset__articles")).values_list("id", "n"))

    def get_n_articles(self, obj):
        if not obj: return 0
        return self._get_n_articles().get(obj.id, 0)

    def get_n_done_jobs(self, obj):
        if not obj: return 0
        return self._get_n_done_jobs().get(obj.id, 0)

    class Meta:
        model = CodingJob

class CodingJobViewSetMixin(ProjectViewSetMixin):
    url = ProjectViewSetMixin.url + "/(?P<project>[0-9]+)/codingjobs"
    model_serializer_class = CodingJobSerializer

    @property
    def codingjob(self):
        return self._codingjob()

    @cached
    def _codingjob(self):
        return CodingJob.objects.get(id=self.kwargs.get("codingjob"))


class CodingJobViewSet(CodingJobViewSetMixin, DatatablesMixin, ModelViewSet):
    model = CodingJob

    def filter_queryset(self, jobs):
        jobs = super(CodingJobViewSet, self).filter_queryset(jobs)
        return jobs.filter(project=self.project)