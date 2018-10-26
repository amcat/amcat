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
from rest_framework import serializers
from rest_framework.viewsets import ReadOnlyModelViewSet
from amcat.models import CodingSchema, CodingSchemaField
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.coding.codingschemafield import CodingSchemaFieldViewSetMixin, CodingSchemaFieldSerializer
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.coding.codingjob import CodingJobViewSetMixin

__all__ = ("CodingSchemaViewSetMixin", "CodingSchemaSerializer", "CodingSchemaViewSet",
            "CodingJobCodingSchemaViewSet", "_CodingSchemaFieldViewSet")


class CodingSchemaSerializer(AmCATModelSerializer):
    highlighters = serializers.SerializerMethodField()

    def get_highlighters(self, obj):
        return [h.pk for h in obj.highlighters.all()]

    class Meta:
        model = CodingSchema
        fields = '__all__'

class CodingSchemaViewSetMixin(AmCATViewSetMixin):
    queryset = CodingSchema.objects.all()
    serializer_class = CodingSchemaSerializer
    model_key = "codingschema"
    model = CodingSchema


class CodingJobCodingSchemaViewSet(ProjectViewSetMixin, CodingJobViewSetMixin,
                                   CodingSchemaViewSetMixin, DatatablesMixin,
                                   ReadOnlyModelViewSet):
    queryset = CodingSchema.objects.all()
    model = CodingSchema
    serializer_class = CodingSchemaSerializer

    def filter_queryset(self, codingschemas):
        return super(CodingJobCodingSchemaViewSet, self).filter_queryset(codingschemas).filter(
            id__in=(self.codingjob.unitschema_id, self.codingjob.articleschema_id)
        )

class CodingSchemaViewSet(ProjectViewSetMixin, CodingSchemaViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    queryset = CodingSchema.objects.all()
    serializer_class = CodingSchemaSerializer
    model = CodingSchema

    def filter_queryset(self, codingschemas):
        codingschemas = super(CodingSchemaViewSet, self).filter_queryset(codingschemas)
        return codingschemas.filter(id__in=self.project.get_codingschemas()).prefetch_related("highlighters")

class _CodingSchemaFieldViewSet(ProjectViewSetMixin, CodingSchemaViewSetMixin, CodingSchemaFieldViewSetMixin,
                                DatatablesMixin, ReadOnlyModelViewSet):
    queryset = CodingSchemaField.objects.all()
    serializer_class = CodingSchemaFieldSerializer
    model = CodingSchemaField

    def filter_queryset(self, fields):
        return super(_CodingSchemaFieldViewSet, self).filter_queryset(fields).filter(codingschema=self.codingschema)
