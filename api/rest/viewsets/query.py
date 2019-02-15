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
import json

from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.fields import Field
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.viewsets import ModelViewSet

from amcat.models import Query, ROLE_PROJECT_WRITER
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets import ProjectViewSetMixin, ProjectPermission

__all__ = ("QuerySerializer", "QueryViewSet")


class ParametersField(Field):
    def __init__(self, *args, **kwargs):
        super(ParametersField, self).__init__(*args, **kwargs)

    def to_representation(self, value):
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                return json.loads(data)
            except ValueError:
                raise ValidationError("No JSON object could be decoded")
        return data


class QuerySerializer(AmCATModelSerializer):
    user = PrimaryKeyRelatedField(read_only=True)
    project = PrimaryKeyRelatedField(read_only=True)
    parameters = ParametersField()

    class Meta:
        model = Query
        fields = '__all__'


class QueryViewSetMixin(AmCATViewSetMixin):
    model = Query
    model_key = "query"
    search_fields = ordering_fields = ("id", "name", "user__username")
    queryset = Query.objects.all()


class QueryViewSet(ProjectViewSetMixin, QueryViewSetMixin, DatatablesMixin, ModelViewSet):
    serializer_class = QuerySerializer
    queryset = Query.objects.all()
    http_method_names = ("get", "options", "post", "put", "patch", "delete")
    permission_classes = (ProjectPermission,)
    permission_map = {
        "PUT": ROLE_PROJECT_WRITER,
        "PATCH": ROLE_PROJECT_WRITER,
        "DELETE": ROLE_PROJECT_WRITER
    }
    ignore_filters = ('parameters',)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user, project=self.project)

    def perform_update(self, serializer):
        return serializer.save(user=self.request.user, project=self.project)

    def filter_queryset(self, queryset):
        queryset = super(QueryViewSet, self).filter_queryset(queryset)
        return queryset.filter(project__id=self.project.id)
