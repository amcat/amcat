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
from amcat.models import CodingSchemaField
from amcat.tools.caching import cached
from api.rest.resources.amcatresource import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewsets import CodingSchemaViewSetMixin

__all__ = ("CodingSchemaFieldViewSetMixin", "CodingSchemaFieldSerializer", "CodingSchemaFieldViewSet")


class CodingSchemaFieldSerializer(AmCATModelSerializer):
    class Meta:
        model = CodingSchemaField

class CodingSchemaFieldViewSetMixin(CodingSchemaViewSetMixin):
    url = CodingSchemaViewSetMixin.url + "/(?P<codingschema>[0-9]+)/fields"
    model_serializer_class = CodingSchemaFieldSerializer

    @property
    def codingschemafield(self):
        return self._codingschemafield()

    @cached
    def _codingschemafield(self):
        return CodingSchemaField.objects.get(id=self.kwargs.get("codingschemafield"))


class CodingSchemaFieldViewSet(CodingSchemaFieldViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = CodingSchemaField

    def filter_queryset(self, fields):
        fields = super(CodingSchemaFieldViewSet, self).filter_queryset(fields)
        return fields.filter(codingschema__in=self.project.get_codingschemas())