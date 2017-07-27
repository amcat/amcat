import datetime
import os
import shutil
import tempfile
from logging import getLogger

import chardet
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import QuerySet

from amcat.tools.model import AmcatModel

log = getLogger(__name__)

EXPIRY_TIME = datetime.timedelta(days=1)
UPLOAD_ROOT = os.path.join(tempfile.gettempdir(), "amcat_upload")

upload_storage = FileSystemStorage(location=UPLOAD_ROOT)

def _get_upload_dir(instance, filename):
    name, ext = os.path.splitext(os.path.basename(filename))
    uploadpath = "./{}/{}".format(upload_storage.get_available_name(name), filename)
    return uploadpath

class UploadedFile(AmcatModel):
    id = models.AutoField(primary_key=True, db_column="upload_id")
    project = models.ForeignKey("amcat.Project")
    user = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to=_get_upload_dir, storage=upload_storage)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_expired()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        try:
            root = os.path.dirname(self.file.name)
            shutil.rmtree(upload_storage.path(root))
        except Exception as e:
            log.warning("Failed to delete file {self.file.name} from upload {self}. Reason: {e}".format(**locals()))
        return super().delete(*args, **kwargs)

    def open_file(self, encoding):
        """Open the file in str (unicode) mode, guessing encoding if needed"""
        binary_content = open(self.file.file.name, mode='rb').read(1000)
        encoding = self._get_encoding(encoding, binary_content)
        return open(self.file.file.name, encoding=encoding)

    def read_file(self, encoding, n=None):
        """Read the file, guessing encoding if needed"""
        binary_content = open(self.file.file.name, mode='rb').read(n)
        encoding = self._get_encoding(encoding, binary_content)
        return binary_content.decode(encoding)

    @property
    def filepath(self) -> str:
        return self.file.file.name

    @property
    def filename(self) -> str:
        return os.path.basename(self.file.name)

    @property
    def is_expired(self) -> bool:
        return datetime.datetime.now() - EXPIRY_TIME >= self.created_at

    @property
    def expires_at(self) -> datetime:
        """The expiry datetime of this upload"""
        return self.created_at + EXPIRY_TIME

    @classmethod
    def get_all_active(cls) -> QuerySet:
        """
        Get all uploads that haven't expired yet.
        """
        expiry_dt = datetime.datetime.now() - EXPIRY_TIME
        return cls.objects.filter(created_at__gt=expiry_dt)

    @classmethod
    def get_all_expired(cls) -> QuerySet:
        """
        Get all uploads that have expired.
        """
        expiry_dt = datetime.datetime.now() - EXPIRY_TIME
        return cls.objects.filter(created_at__lte=expiry_dt)

    @classmethod
    def delete_expired(cls):
        """
        Deletes all expired uploads.
        @return: The deleted uploads
        """
        expired = cls.get_all_expired()
        # delete one by one so instance.delete can clean up the files
        for instance in expired:
            instance.delete()
        return expired

    @staticmethod
    def _get_encoding(encoding, binary_content):
        if encoding.lower() == "autodetect":
            encoding = chardet.detect(binary_content)["encoding"]
            if encoding == "ascii":
                encoding = "utf-8"
            log.info("Guessed encoding: {encoding}".format(**locals()))
        return encoding

    class Meta:
        app_label = 'amcat'
        db_table = 'uploadedfiles'
