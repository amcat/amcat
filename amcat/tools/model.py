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

from django.db import models
from django_extensions.db.fields import UUIDField

__all__ = ['AmcatModel', 'PostgresNativeUUIDField']


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


