from rest_framework.fields import CharField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.viewsets import ModelViewSet

from amcat.models import ProjectUploadPlugin, ROLE_PROJECT_WRITER
from api.rest.mixins import AmCATFilterMixin
from api.rest.serializer import AmCATProjectModelSerializer
from api.rest.viewsets import ProjectPermission, ProjectViewSetMixin


class UploadPluginSerializer(AmCATProjectModelSerializer):
    project = PrimaryKeyRelatedField(read_only=True)
    name = CharField(read_only=True)
    class Meta:
        model = ProjectUploadPlugin

class UploadPluginViewSet(ProjectViewSetMixin, AmCATFilterMixin, ModelViewSet):
    model = ProjectUploadPlugin
    model_key = "upload_plugin"
    basename = "project-upload_plugins"
    queryset = ProjectUploadPlugin.objects.all()
    serializer_class = UploadPluginSerializer
    search_fields = ordering_fields = ("name", "enabled", "id")
    http_method_names = ("get", "options", "post", "put", "patch", "delete")
    permission_classes = (ProjectPermission,)
    permission_map = {
        "PUT": ROLE_PROJECT_WRITER,
        "PATCH": ROLE_PROJECT_WRITER,
        "DELETE": ROLE_PROJECT_WRITER
    }

    def perform_create(self, serializer):
        return serializer.save(project=self.project)

    def perform_update(self, serializer):
        return serializer.save(project=self.project)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset.filter(project__id=self.project.id)
