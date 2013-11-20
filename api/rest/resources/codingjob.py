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
from rest_framework.viewsets import ModelViewSet

from amcat.tools.caching import cached
from amcat.models import CodingJob
from amcat.models.coding import coding
from api.rest.resources.amcatresource import AmCATResource
from api.rest.resources.amcatresource import DatatablesMixin
from api.rest.serializers.codingjob import CodingJobSerializer

from api.rest.viewsets import (ProjectViewSetMixin   )



class CodingJobResource(AmCATResource):
    model = CodingJob
    serializer_class = CodingJobSerializer


class CodingJobViewSet(ProjectViewSetMixin, DatatablesMixin, ModelViewSet):
    model = CodingJob
    url = 'projects/(?P<project>[0-9]+)/codingjobs'
    model_serializer_class = CodingJobSerializer

    def filter_queryset(self, jobs):
        jobs = super(CodingJobViewSet, self).filter_queryset(jobs)
        return jobs.filter(project=self.project)

class CodingjobViewSetMixin(ProjectViewSetMixin):
    url = "projects/(?P<project>[0-9]+)/codingjobs"
    model_serializer_class = CodingJobSerializer

    @property
    def codingjob(self):
        return self._codingjob()

    @cached
    def _codingjob(self):
        return CodingJob.objects.get(id=self.kwargs.get("codingjob"))

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
from api.rest.apitestcase import ApiTestCase
from django.test.client import RequestFactory

class TestCodingJobResource(ApiTestCase):
    def setUp(self):
        super(TestCodingJobResource, self).setUp()
        self.factory = RequestFactory()

    def _test_caching(self):
        """DISABLED: Queries not registered??"""
        from django.core.urlresolvers import reverse

        cj = amcattest.create_test_job()
        req = self.factory.get(reverse("api-v4-codingjob"))

        with self.checkMaxQueries(1):
            res = CodingJobResource().dispatch(req)

    def test_api(self):
        from amcat.models import CodingStatus

        cj = amcattest.create_test_job()

        # Test empty codingjob
        res = self.get(CodingJobResource, id=cj.id)['results'][0]
        self.assertTrue("n_codings_done" in res)
        self.assertTrue("n_articles" in res)
        self.assertEquals(1, res["n_articles"])
        self.assertEquals(0, res["n_codings_done"])

        # Add two codings
        cj.codings.add(amcattest.create_test_coding(), amcattest.create_test_coding())
        res = self.get(CodingJobResource, id=cj.id)['results'][0]
        self.assertEquals(1, res["n_articles"])
        self.assertEquals(0, res["n_codings_done"])

        # Set one coding to done
        cd= cj.codings.all()[0]
        cd.status = CodingStatus.objects.get(id=coding.STATUS_COMPLETE)
        cd.save()

        res = self.get(CodingJobResource, id=cj.id)['results'][0]
        self.assertEquals(1, res["n_codings_done"])

        cd.status = CodingStatus.objects.get(id=coding.STATUS_IRRELEVANT)
        cd.save()

        res = self.get(CodingJobResource, id=cj.id)['results'][0]
        self.assertEquals(1, res["n_codings_done"])

