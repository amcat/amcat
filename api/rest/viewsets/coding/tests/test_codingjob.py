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
from unittest import skip

from django.db.models import QuerySet
from amcat.models import STATUS_COMPLETE, STATUS_IRRELEVANT, CodingJob
from amcat.tools.amcattest import AmCATTestCase
from api.rest.viewsets import CodingJobSerializer


class TestCodingJobSerializer(AmCATTestCase):
    # Simulating request
    class View(object):
        def get_queryset(self):
            return self.queryset

        def filter_queryset(self, queryset):
            return queryset

        def __init__(self, objs):
            if not isinstance(objs, QuerySet):
                self.queryset = CodingJob.objects.filter(id=objs.id)
            else:
                self.queryset = objs


    def _get_serializer(self, codingjob):
        return CodingJobSerializer(context={"view": self.View(codingjob)})

    def test_get_n_done_jobs(self):
        from amcat.tools import amcattest
        from amcat.models.coding.codedarticle import CodedArticleStatus, STATUS_INPROGRESS

        codingjob = amcattest.create_test_job(10)
        s = self._get_serializer(codingjob)
        self.assertEqual(0, s.get_n_done_jobs(codingjob))
        self.assertEqual(10, codingjob.coded_articles.all().count())

        ca, ca2, ca3 = codingjob.coded_articles.all()[0:3]
        ca.status = CodedArticleStatus.objects.get(id=STATUS_COMPLETE)
        ca.save()

        s = self._get_serializer(codingjob)
        self.assertEqual(1, s.get_n_done_jobs(codingjob))
        self.assertEqual(10, codingjob.coded_articles.all().count())

        ca2.status = CodedArticleStatus.objects.get(id=STATUS_IRRELEVANT)
        ca2.save()

        s = self._get_serializer(codingjob)
        self.assertEqual(2, s.get_n_done_jobs(codingjob))
        self.assertEqual(10, codingjob.coded_articles.all().count())

        ca2.status = CodedArticleStatus.objects.get(id=STATUS_INPROGRESS)
        ca2.save()
        self.assertEqual(2, s.get_n_done_jobs(codingjob))

    def test_get_n_articles(self):
        from amcat.tools import amcattest
        codingjob1 = amcattest.create_test_job(10)
        codingjob2 = amcattest.create_test_job(5)

        jobs = CodingJob.objects.filter(id__in=[codingjob1.id, codingjob2.id])
        s = self._get_serializer(jobs)
        self.assertEqual(10, s.get_n_articles(codingjob1))
        self.assertEqual(5, s.get_n_articles(codingjob2))

    @skip("This is not a great idea. Serializers are short lived, so caching all codingjobs every time "
          "would require a lot of resources.")
    def test_n_queries(self):
        from amcat.tools import amcattest

        codingjob1 = amcattest.create_test_job(10)
        codingjob2 = amcattest.create_test_job(5)
        jobs = CodingJob.objects.filter(id__in=[codingjob1.id, codingjob2.id])
        s = self._get_serializer(jobs)

        # Number of codingjobs should be cached for all codingsjobs after one call
        with self.checkMaxQueries(1):
            s.get_n_articles(codingjob1)
            s.get_n_articles(codingjob2)

        # Same for done jobs
        s = self._get_serializer(jobs)
        with self.checkMaxQueries(1):
            s.get_n_done_jobs(codingjob1)
            s.get_n_done_jobs(codingjob2)