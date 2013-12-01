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
from api.rest.viewsets.coding.coded_article import CodedArticleViewSetMixin
from api.rest.viewsets.sentence import SentenceSerializer

__all__ = (
    "CodingSerializer", "CodingViewSetMixin", "CodingViewSet", "CodedArticleSentenceViewSet",
    "CodingValueViewSet", "CodingValueSerializer",
)

class CodingSerializer(AmCATModelSerializer):
    model = Coding

class CodingViewSetMixin(CodedArticleViewSetMixin):
    url = CodedArticleViewSetMixin.url + "/(?P<article>[0-9]+)/codings"
    model_serializer_class = CodingSerializer

class CodingViewSet(CodingViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = Coding

    @property
    def coding(self):
        return self._coding()

    @cached
    def _coding(self):
        return Coding.objects.get(id=self.kwargs.get("coding"))

    def filter_queryset(self, queryset):
        qs = super(CodingViewSet, self).filter_queryset(queryset)
        return qs.filter(codingjob=self.codingjob, article=self.article)


class CodingValueSerializer(AmCATModelSerializer):
    model = CodingValue

class CodingValueViewSet(CodedArticleViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    url = CodedArticleViewSetMixin.url + "/(?P<article>[0-9]+)/coding_values"
    model_serializer_class = CodingValueSerializer
    model = CodingValue

    def filter_queryset(self, queryset):
        qs = super(CodingValueViewSet, self).filter_queryset(queryset)
        return qs.filter(coding__codingjob=self.codingjob, coding__article=self.article)

class CodedArticleSentenceViewSet(CodedArticleViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    url = CodedArticleViewSetMixin.url + "/(?P<article>[0-9]+)/sentences"
    model_serializer_class = SentenceSerializer
    model = Sentence

    def filter_queryset(self, queryset):
        qs = super(CodedArticleSentenceViewSet, self).filter_queryset(queryset)
        return qs.filter(article=self.article)

