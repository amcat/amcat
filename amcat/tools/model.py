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

import binascii

from django.db import models
from django_extensions.db.fields import UUIDField

__all__ = ['AmcatModel', 'PostgresNativeUUIDField', 'Hash', 'HashField']


class AmcatModel(models.Model):
    """Replacement for standard Django-model, extending it with
    amcat-specific features."""
    __label__ = 'label'

    class Meta():
        abstract = True
        app_label = "model"

    def __str__(self):
        try:
            return str(getattr(self, self.__label__))
        except AttributeError:
            return str(self.id)

    @classmethod
    def get_or_create(cls, **attributes):
        try:
            return cls.objects.get(**attributes)
        except cls.DoesNotExist:
            return cls.objects.create(**attributes)


class PostgresNativeUUIDField(UUIDField):
    """
    Improvement to django_extensions.db.fields.UUIDField to use postgres
    internal UUID field type rather than char for storage.
    
    """

    def db_type(self, connection=None):
        if connection and connection.vendor in ("postgresql",):
            return "UUID"
        return super(UUIDField, self).db_type(connection=connection)


class Hash:
    """
    A simple class representing hashes.
    """
    def __init__(self, hash):
        """
        Initiates the hash with either a str in hex format, or the raw bytes.
        """
        if isinstance(hash, Hash):
            self.bytes = hash.bytes
        elif isinstance(hash, str):
            self.bytes = binascii.unhexlify(hash)
        elif isinstance(hash, bytes):
            self.bytes = hash
        else:
            raise ValueError("Hash must be either a hex string or raw bytes.")


    def __len__(self):
        """
        Returns the length of the hash in bytes.
        """
        return len(self.bytes)

    def __str__(self):
        """
        Returns a hexadecimal str representing the hash.
        """
        return binascii.hexlify(self.bytes).decode("ascii")

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, str(self))

    def __bytes__(self):
        return self.bytes

    def __eq__(self, other):
        if isinstance(other, Hash):
            return self.bytes == other.bytes
        if isinstance(other, bytes):
            return self.bytes == other
        if isinstance(other, str):
            return str(self) == other
        return False

class HashField(models.BinaryField):
    description = ('HashField is related to some other field in a model and'
                   'stores its hashed value for better indexing performance.')

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('db_index', True)
        kwargs.setdefault('editable', False)
        super(HashField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if value:
            return Hash(value)

    def from_db_value(self, value, expression, connection, context):
        if value:
            hash = Hash(bytes(value))
            return hash

    def get_prep_value(self, value):
        if value:
            if len(value) < self.max_length:
                value = value.rjust(self.max_length, b'\0')
            return bytes(Hash(value))
