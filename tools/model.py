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

import json

class AmcatModel(models.Model):
    """Replacement for standard Django-model, extending it with
    amcat-specific features."""
    def save(self, **kwargs):
        """TODO"""
        super(AmcatModel, self).save(**kwargs)

    def can_read(self, user):
        """Determine if `user` has read access to this object.

        @return: boolean"""
        return True

    def can_update(self, user):
        """Determine if `user` has write access to this object.

        @return: boolean"""
        return True

    def can_create(self, user):
        return self.can_update(user)

    def can_delete(self, user):
        return self.can_update(user)

    class Meta():
        # https://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes
        abstract=True
        app_label = "model"

class JSONField(models.TextField):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        if 'default' not in kwargs:
            kwargs.update(dict(default='{}'))
        super(JSONField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, basestring):
            return json.loads(value)
        return value

    def get_prep_value(self, value):
        return json.dumps(value)