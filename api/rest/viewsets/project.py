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
from datetime import datetime

from rest_framework import serializers, permissions, exceptions, status
from rest_framework.viewsets import ModelViewSet, ViewSetMixin

import settings
from amcat.models import Project, Role
from amcat.tools.caching import cached
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATProjectModelSerializer
from amcat.models.authorisation import (ROLE_PROJECT_READER, ROLE_PROJECT_WRITER,
                                        ROLE_PROJECT_ADMIN, ROLE_PROJECT_METAREADER)

import logging
from api.rest.viewset import AmCATViewSetMixin

log = logging.getLogger(__name__)

__all__ = ("CannotEditLinkedResource", "NotFoundInProject", "ProjectPermission",
            "ProjectViewSetMixin", "ProjectSerializer", "ProjectViewSet")

_DEFAULT_PERMISSION_MAP = {
    'OPTIONS' : True,
    'HEAD' : True,
    'GET' : ROLE_PROJECT_METAREADER,
    'POST' : ROLE_PROJECT_WRITER,
    'PUT' : False,
    'PATCH' : ROLE_PROJECT_ADMIN,
    'DELETE' : ROLE_PROJECT_ADMIN,
}

class CannotEditLinkedResource(exceptions.PermissionDenied):
    default_detail = 'Cannot modify a linked resource, please edit via the owning project'

class NotFoundInProject(exceptions.APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'The requested resource does not exist in the given project'
    def __init__(self, detail=None):
        self.detail = detail or self.default_detail

class OptionalIsAuthenticated(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if not settings.amcat_config.get('auth', 'require_login'):
            return True
        return super().has_permission(request, view)


class ProjectPermission(permissions.BasePermission):
    """
    Checks permissions based on the user's project role
    Uses view.permission_map, defaulting to _DEFAULT_PERMISSIONS_MAP
    Assumes .project is defined on the view
    """

    def has_permission(self, request, view):
        # When viewing project lists, no project is in context
        if view.project is None:
            return True



        user = request.user if request.user.is_authenticated() else None
        if user and user.is_superuser:
            return True

        required_role_id = view.required_role_id(request)

        if required_role_id in (True, False):
            return required_role_id

        actual_role_id = view.project.get_role_id(user=user)
        if actual_role_id is None or actual_role_id < required_role_id:
            log.warn("User {user} has role {actual_role_id} < {required_role_id}".format(**locals()))

        if actual_role_id is None:
            return False
        return actual_role_id >= required_role_id


class ProjectSerializer(AmCATProjectModelSerializer):
    """
    This serializer includes another boolean field `favourite` which is is True
    when the serialized project is in request.user.user_profile.favourite_projects.
    """
    favourite = serializers.SerializerMethodField("is_favourite")
    last_visited_at = serializers.SerializerMethodField("project_visited_at", allow_null=True)

    @property
    @cached
    def favourite_projects(self):
        """List of id's of all favourited projects by the currently logged in user"""
        user = self.context['request'].user
        if user.is_anonymous():
            return set()
        else:
            return set(self.context['request'].user.userprofile
                       .favourite_projects.values_list("id", flat=True))

    def is_favourite(self, project):
        if project is None: return
        return project.id in self.favourite_projects

    @property
    @cached
    def project_visited_dates(self):
        user = self.context['request'].user
        if user.is_anonymous():
            return dict()

        return dict((rp.project, rp.format_date_visited_as_delta()) for rp in user.userprofile.get_recent_projects())

    def project_visited_at(self, project):
        return self.project_visited_dates.get(project, "Never")

    def get_fields(self):
        fields = super(ProjectSerializer, self).get_fields()

        #push last_visited_at on top for better column ordering
        fields['last_visited_at'] = fields.pop('last_visited_at')
        return fields

    class Meta:
        model = Project

class ProjectViewSetMixin(AmCATViewSetMixin):
    permission_classes = (OptionalIsAuthenticated, ProjectPermission)
    serializer_class = ProjectSerializer
    model_key = "project"
    queryset = Project.objects.all()


    def required_role_id(self, request):
        required_role_id = getattr(self, 'permission_map', {}).get(request.method.upper())
        if required_role_id is None:
            required_role_id = _DEFAULT_PERMISSION_MAP[request.method.upper()]
        return required_role_id
    
class ProjectViewSet(ProjectViewSetMixin, DatatablesMixin, ModelViewSet):
    model = Project

    @property
    def project(self):
        if 'pk' in self.kwargs:
            return Project.objects.get(pk=self.kwargs['pk'])
        else:
            return None # no permissions needed. Not a very elegant signal?

    def filter_queryset(self, queryset):
        qs = super(ProjectViewSet, self).filter_queryset(queryset)
        role = Role.objects.get(label="metareader")
        if self.request.user.is_anonymous():
            return qs.filter(guest_role__id__gte=role.id)
        else:
            return qs.filter(id__in=self.request.user.userprofile.get_projects(role))
