from django.contrib.auth.models import User
from django.views.generic import RedirectView
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, reverse
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from amcat.models import ProjectRole, PROJECT_ROLES, ROLE_PROJECT_ADMIN
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets import ProjectViewSetMixin


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        exclude = ("groups", "user_permissions")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.set_password(validated_data['password'])
        instance.save()
        return instance


class UserViewSetMixin(AmCATViewSetMixin):
    model = User
    model_key = "user"
    queryset = User.objects.all()


class UserViewPermission(BasePermission):
    def has_permission(self, request, view):
        object = view.get_object()
        if view.action != "list" and object == request.user:
            return True
        if request.method in ("GET", "POST", "OPTIONS"):
            return request.user.is_staff
        elif request.method in ("DELETE", "PUT"):
            return request.user.is_superuser
        return False


class UserViewSet(UserViewSetMixin, ModelViewSet):
    queryset = User.objects.all()
    permission_classes = (UserViewPermission,)
    serializer_class = UserSerializer

    def get_object(self):
        if 'pk' not in self.kwargs:
            return None
        if self.kwargs.get('pk') == "me":
            return self.request.user
        return super().get_object()



class ProjectRoleSerializer(ModelSerializer):
    class Meta:
        model = ProjectRole


class ProjectRoleViewSetMixin(AmCATViewSetMixin):
    model_key = "role"
    model = ProjectRole
    #search_fields = ordering_fields = ("id", "name", "provenance")
    queryset = ProjectRole.objects.all()

class ProjectRoleViewSet(ProjectViewSetMixin, ProjectRoleViewSetMixin, ModelViewSet):
    model = ProjectRole
    queryset = ProjectRole.objects.all()
    serializer_class = ProjectRoleSerializer
    permission_map = {'POST': ROLE_PROJECT_ADMIN}

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        # If the user already exists in this project, change request into a modification
        pid = request.data.get('project')
        uid = request.data.get('user')
        if pid and uid:
            try:
                p = ProjectRole.objects.get(project_id=pid, user_id=uid)
            except ProjectRole.DoesNotExist:
                # add new user
                return super().create(request, *args, **kwargs)
            else:
                # modify the user
                self.kwargs['pk'] = p.pk
                return self.update(request, *args, **kwargs)


    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset.filter(project=self.project)