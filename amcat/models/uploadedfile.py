import codecs
import datetime
import functools
import os
import shutil
import tempfile
import zipfile
from logging import getLogger
from typing import Iterable

import chardet
from django.contrib.auth.models import User
import django.core.files.uploadedfile
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import QuerySet

from amcat.scripts.article_upload import magic
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

    @property
    def filepath(self) -> str:
        return self.file.file.name

    @property
    def basename(self) -> str:
        return os.path.basename(self.file.name)

    @property
    def is_expired(self) -> bool:
        return datetime.datetime.now() - EXPIRY_TIME >= self.created_at

    @property
    def expires_at(self) -> datetime:
        """The expiry datetime of this upload"""
        return self.created_at + EXPIRY_TIME

    @property
    @functools.lru_cache()
    def file_info(self) -> str:
        return magic.get_mime(self.filepath)

    @property
    def mime_type(self) -> str:
        return self.file_info[0]

    @property
    def is_zip(self) -> str:
        return self.file_info[2]

    @functools.lru_cache()
    def count(self):
        if self.is_zip:
            return len([m for m in self.zipfile.namelist() if not m.endswith("/")])
        return 1

    @property
    def encoding(self) -> str:
        if not hasattr(self, "_encoding"):
            if self.is_zip:
                first_entry = next(m for m in self.zipfile.namelist() if not m.endswith("/"))
                content = self.zipfile.read(first_entry)
            else:
                content = open(self.file.file.name, mode='rb').read(1000)
            self._encoding = self._guess_encoding(content)
        return self._encoding

    @property
    @functools.lru_cache()
    def zipfile(self):
        if not self.is_zip:
            raise AttributeError
        return zipfile.ZipFile(self.filepath)


    def get_files(self) -> Iterable[django.core.files.uploadedfile.UploadedFile]:
        if self.is_zip:
            yield from self._unpack()
            return

        yield self._open(self.filepath, self.basename)

    def encoding_override(self, encoding: str):
        """
        Override the encoding with a fixed value.
        @param encoding:
        @return:
        """
        if not encoding or encoding.lower() == "autodetect":
            return
        elif encoding.lower() == "binary":
            self._encoding = "binary"
            return
        try:
            codecs.lookup(encoding)
        except LookupError:
            raise LookupError("The given codec ({}) does not exist".format(encoding))
        self._encoding = encoding

    def _unpack(self) -> Iterable[django.core.files.uploadedfile.UploadedFile]:
        path = "{}/{}".format(os.path.dirname(self.filepath), os.path.splitext(self.basename)[0])
        os.makedirs(path, exist_ok=True)
        archive_name = os.path.basename(self.zipfile.filename)
        for member in self.zipfile.namelist():
            if member.endswith("/"):
                continue
            fn = os.path.join(path, member)
            if not os.path.isfile(fn):
                self.zipfile.extract(member, os.path.dirname(fn))
            f = self._open(fn, member)
            setattr(f, "archive_name", archive_name)
            yield f

    def _open(self, path: str, name: str) -> django.core.files.uploadedfile.UploadedFile:
        if self.encoding == "binary":
            return django.core.files.uploadedfile.UploadedFile(open(path, mode="rb"), name=name,
                                                               content_type=self.mime_type)
        else:
            return django.core.files.uploadedfile.UploadedFile(open(path, encoding=self.encoding), name=name,
                                                               content_type=self.mime_type, charset=self.encoding)


    def __iter__(self) -> Iterable[django.core.files.uploadedfile.UploadedFile]:
        return self.get_files()

    def __len__(self) -> int:
        return self.count()

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
    def _guess_encoding(binary_content):
        encoding = chardet.detect(binary_content)["encoding"]
        if encoding is None:
            encoding = "binary"
        elif encoding == "ascii":
            encoding = "utf-8"
        return encoding

    class Meta:
        app_label = 'amcat'
        db_table = 'uploadedfiles'
