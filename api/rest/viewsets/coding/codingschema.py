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
from api.rest.viewsets.project import ProjectViewSetMixin

__all__ = ("CodingSchemaViewSetMixin", "CodingSchemaSerializer", "CodingSchemaViewSet")


class CodingSchemaSerializer(AmCATModelSerializer):
    class Meta:
        model = CodingSchema

class CodingSchemaViewSetMixin(ProjectViewSetMixin):
    url = ProjectViewSetMixin.url + "/(?P<project>[0-9]+)/codingschemas"
    model_serializer_class = CodingSchemaSerializer

    @property
    def codingschema(self):
        return self._codingschema()

    @cached
    def _codingschema(self):
        return CodingSchema.objects.get(id=self.kwargs.get("codingschema"))


class CodingSchemaViewSet(CodingSchemaViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = CodingSchema

    def filter_queryset(self, codingschema):
        codingschema = super(CodingSchemaViewSet, self).filter_queryset(codingschema)
        return codingschema.filter(id__in=self.project.get_codingschemas())