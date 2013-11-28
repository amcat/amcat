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
from rest_framework.viewsets import ReadOnlyModelViewSet
from amcat.models import Coding, Sentence, CodingValue
from amcat.tools.caching import cached
from api.rest.resources.amcatresource import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.coding.codingjob import CodingJobViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.coding.coded_article import CodedArticleViewSetMixin
from api.rest.viewsets.sentence import SentenceSerializer, SentenceViewSetMixin

__all__ = (
    "CodingSerializer", "CodingViewSetMixin", "CodingViewSet", "CodedArticleSentenceViewSet",
    "CodingValueViewSet", "CodingValueSerializer",
)

class CodingSerializer(AmCATModelSerializer):
    model = Coding

class CodingViewSetMixin(AmCATViewSetMixin):
    model_serializer_class = CodingSerializer
    model_key = "coding"
    model = Coding

class CodingViewSet(ProjectViewSetMixin, CodingJobViewSetMixin,
                    CodingViewSetMixin, DatatablesMixin,
                    ReadOnlyModelViewSet):
    model = Coding

    def filter_queryset(self, queryset):
        qs = super(CodingViewSet, self).filter_queryset(queryset)
        return qs.filter(codingjob=self.codingjob, article=self.article)


class CodingValueSerializer(AmCATModelSerializer):
    model = CodingValue

class CodingValueViewSetMixin(AmCATViewSetMixin):
    model_serializer_class = CodingValueSerializer
    model_key = "codingvalue"
    model = CodingValue


class CodingValueViewSet(ProjectViewSetMixin, CodingJobViewSetMixin,
                         CodedArticleViewSetMixin, CodingViewSetMixin,
                         CodingValueViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = CodingValue

    def filter_queryset(self, queryset):
        qs = super(CodingValueViewSet, self).filter_queryset(queryset)
        return qs.filter(coding__codingjob=self.codingjob, coding__article=self.article)

class CodedArticleSentenceViewSet(ProjectViewSetMixin, CodingJobViewSetMixin,
                                  CodedArticleViewSetMixin, SentenceViewSetMixin,
                                  DatatablesMixin, ReadOnlyModelViewSet):
    model = Sentence

    def filter_queryset(self, queryset):
        qs = super(CodedArticleSentenceViewSet, self).filter_queryset(queryset)
        return qs.filter(article=self.article)

