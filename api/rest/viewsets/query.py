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

from django.core.validators import BaseValidator
from django.db.models import Q
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.viewsets import ModelViewSet
from rest_framework.fields import Field

from amcat.models import Query, ROLE_PROJECT_WRITER
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewsets import ProjectViewSetMixin, ProjectPermission


__all__ = ("QuerySerializer", "QueryViewSet")


class ParametersField(Field):
    def __init__(self, *args, **kwargs):
        super(ParametersField, self).__init__(*args, **kwargs)

    def to_representation(self, value):
        if isinstance(value, basestring):
            return value
        return json.dumps(value)

    def to_internal_value(self, data):
        if isinstance(data, basestring):
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


class QueryPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        public_and_get = request.method == "GET" and not obj.private
        public_or_owned = request.user.is_superuser or obj.user_id == request.user.id or public_and_get
        return public_or_owned

class QueryViewSet(ProjectViewSetMixin, DatatablesMixin, ModelViewSet):
    model = Query
    model_key = "query"
    serializer_class = QuerySerializer
    queryset = QuerySerializer.Meta.model.objects.all()
    search_fields = ordering_fields = ("id", "name", "user__username")
    http_method_names = ("get", "options", "post", "put", "patch", "delete")
    permission_classes = (QueryPermission, ProjectPermission)
    permission_map = {
        "PUT": ROLE_PROJECT_WRITER,
        "PATCH": ROLE_PROJECT_WRITER,
        "DELETE": ROLE_PROJECT_WRITER
    }

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user, project=self.project)

    def perform_update(self, serializer):
        return serializer.save(user=self.request.user, project=self.project)

    def filter_queryset(self, queryset):
        queryset = super(QueryViewSet, self).filter_queryset(queryset)
        non_private_or_owned = Q(private=False) | Q(user__id=self.request.user.id)
        return queryset.filter(project__id=self.project.id).filter(non_private_or_owned)

