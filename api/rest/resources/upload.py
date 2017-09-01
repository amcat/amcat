import datetime

from rest_framework import serializers

from amcat.models import OrderedDict, UploadedFile
from api.rest.resources import AmCATResource
from api.rest.serializer import AmCATModelSerializer


class UploadSerializer(AmCATModelSerializer):
    expires_in = serializers.SerializerMethodField("_expires_in")
    filename = serializers.SerializerMethodField("_filename")

    def _filename(self, upload):
        return upload.basename

    def _expires_in(self, upload):
        time, unit = (upload.expires_at - datetime.datetime.now()).total_seconds() // 3600, "hour(s)"
        if time == 0:
            time, unit = (upload.expires_at - datetime.datetime.now()).total_seconds() // 60, "minute(s)"
        return "{} {}".format(int(time), unit)

    def get_fields(self):
        fields = OrderedDict(super().get_fields())
        fields.move_to_end('filename', last=False)
        fields.move_to_end('id', last=False)
        return fields

    class Meta:
        model = UploadedFile
        exclude = ["file"]


class UploadResource(AmCATResource):
    model = UploadedFile
    serializer_class = UploadSerializer
    queryset = UploadedFile.get_all_active()
