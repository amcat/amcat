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
from amcat.models import CodingJob, CodingSchema
from amcat.tools.caching import cached
from api.rest.resources.amcatresource import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.coding.codingjob import CodingJobViewSetMixin

__all__ = ("CodingSchemaViewSetMixin", "CodingSchemaSerializer", "CodingSchemaViewSet",
            "CodingJobCodingSchemaViewSet")


class CodingSchemaSerializer(AmCATModelSerializer):
    class Meta:
        model = CodingSchema

class CodingSchemaViewSetMixin(AmCATViewSetMixin):
    model_serializer_class = CodingSchemaSerializer
    model_key = "codingschema"

    @property
    def codingschema(self):
        return self._codingschema()

    @cached
    def _codingschema(self):
        return CodingSchema.objects.get(id=self.kwargs.get("codingschema"))


class CodingJobCodingSchemaViewSet(ProjectViewSetMixin, CodingJobViewSetMixin,
                                   CodingSchemaViewSetMixin, DatatablesMixin,
                                   ReadOnlyModelViewSet):
    model = CodingSchema

    def filter_queryset(self, codingschemas):
        return super(CodingJobCodingSchemaViewSet, self).filter_queryset(codingschemas).filter(
            id__in=(self.codingjob.unitschema_id, self.codingjob.articleschema_id)
        )

class CodingSchemaViewSet(ProjectViewSetMixin, CodingSchemaViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = CodingSchema

    def filter_queryset(self, codingschemas):
        codingschemas = super(CodingSchemaViewSet, self).filter_queryset(codingschemas)
        return codingschemas.filter(id__in=self.project.get_codingschemas())