from abc import ABC
from typing import Union, Iterable

import binascii
import hashlib

from django.db import models

HASH = hashlib.sha224


class Digest:
    """
    A simple class representing hash digests.
    """
    def __init__(self, hash: Union[str, bytes, 'Digest']) -> None:
        """
        Initiates the hash with either a str in hex format, or the raw bytes.
        """
        if isinstance(hash, Digest):
            self.bytes = hash.bytes
        elif isinstance(hash, str):
            self.bytes = binascii.unhexlify(hash)
        elif isinstance(hash, bytes):
            self.bytes = hash
        else:
            raise ValueError("Hash must be either a hex string or raw bytes.")

    def __len__(self) -> int:
        """Returns the length of the digest in bytes."""
        return len(self.bytes)

    def __str__(self) -> str:
        """Returns a hexadecimal str representing the digest."""
        return binascii.hexlify(self.bytes).decode("ascii")

    def __repr__(self) -> str:
        return "{}('{}')".format(self.__class__.__name__, str(self))

    def __bytes__(self) -> bytes:
        """Returns the digest as raw binary data."""
        return self.bytes

    def __eq__(self, other) -> bool:
        if isinstance(other, Digest):
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

    def to_python(self, value) -> Digest:
        if value:
            return Digest(value)

    def from_db_value(self, value, expression, connection, context):
        if value:
            hash = Digest(bytes(value))
            return hash

    def get_prep_value(self, value) -> bytes:
        if value:
            if len(value) < self.max_length:
                value = value.rjust(self.max_length, b'\0')
            return bytes(Digest(value))