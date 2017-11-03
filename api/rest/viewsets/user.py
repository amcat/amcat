from django.contrib.auth.models import User
from django.views.generic import RedirectView
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, reverse
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from api.rest.viewset import AmCATViewSetMixin

class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        exclude = ("groups", "user_permissions")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.set_password(validated_data['password'])
        return instance


class UserViewSetMixin(AmCATViewSetMixin):
    model = User
    model_key = "user"
    queryset = User.objects.all()


class UserViewPermission(BasePermission):
    def has_permission(self, request, view):
        if view.action != "list" and view.get_object() == request.user:
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
        if self.kwargs.get('pk') == "me":
            return self.request.user
        return super().get_object()


