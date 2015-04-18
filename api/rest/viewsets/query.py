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
from django.db.models import Q
from rest_framework import permissions
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.viewsets import ModelViewSet

from amcat.models import Query, ROLE_PROJECT_WRITER
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewsets import ProjectViewSetMixin, ProjectPermission


__all__ = ("QuerySerializer", "QueryViewSet")


class QuerySerializer(AmCATModelSerializer):
    user = PrimaryKeyRelatedField(read_only=True)
    project = PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Query


class QueryPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser or obj.user_id == request.user.id


class QueryViewSet(ProjectViewSetMixin, DatatablesMixin, ModelViewSet):
    model_key = "query"
    model_serializer_class = QuerySerializer
    model = QuerySerializer.Meta.model
    search_fields = ordering_fields = ("id", "name")
    permission_map = {"PUT": ROLE_PROJECT_WRITER, "PATCH": ROLE_PROJECT_WRITER}
    http_method_names = ("get", "options", "post", "put", "patch")
    permission_classes = (QueryPermission, ProjectPermission)

    def pre_save(self, obj):
        #self.check_object_permissions(self.request, obj)
        obj.project = self.project
        obj.user = self.request.user
        return obj

    def filter_queryset(self, queryset):
        queryset = super(QueryViewSet, self).filter_queryset(queryset)
        non_private_or_owned = Q(private=False) | Q(user__id=self.request.user.id)
        return queryset.filter(project__id=self.project.id).filter(non_private_or_owned)

