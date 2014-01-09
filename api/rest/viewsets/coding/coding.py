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
from collections import defaultdict
from rest_framework import serializers
from rest_framework.viewsets import ReadOnlyModelViewSet
from amcat.models import Coding, CodingValue
from amcat.tools.caching import cached
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.coding.codingjob import CodingJobViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.coding.coded_article import CodedArticleViewSetMixin

__all__ = (
    "CodingSerializer", "CodingViewSetMixin", "CodingViewSet",
    "CodingValueViewSet", "CodingValueSerializer",
)

class CodingSerializer(AmCATModelSerializer):
    """
    Serialises Coding-objects, including their values.
    """
    model = Coding
    values = serializers.SerializerMethodField('get_coding_values')

    @cached
    def _get_coding_values(self):
        coding_values = CodingValue.objects.filter(coding__in=self.context["view"].object_list)
        coding_values_dict = defaultdict(list)

        for coding_value in coding_values:
            coding_values_dict[coding_value.coding_id].append({
                "id" : coding_value.id,
                "field" : coding_value.field_id,
                "strval" : coding_value.strval,
                "intval" : coding_value.intval
            })

        return coding_values_dict


    def get_coding_values(self, coding):
        return self._get_coding_values()[coding.pk]

class CodingViewSetMixin(AmCATViewSetMixin):
    model_serializer_class = CodingSerializer
    model_key = "coding"
    model = Coding

class CodingViewSet(ProjectViewSetMixin, CodingJobViewSetMixin,
                    CodedArticleViewSetMixin, CodingViewSetMixin,
                    DatatablesMixin, ReadOnlyModelViewSet):
    model = Coding
    model_serializer_class = CodingSerializer

    def filter_queryset(self, queryset):
        qs = super(CodingViewSet, self).filter_queryset(queryset)
        return qs.filter(coded_article=self.coded_article)


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
        return qs.filter(coding__codingjob=self.codingjob, coding__article=self.coded_article)

