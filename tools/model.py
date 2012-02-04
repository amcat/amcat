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

from django.conf import settings
from django.db import models
from django.db import connections, DEFAULT_DB_ALIAS

from django.core.exceptions import ValidationError

import copy

__all__ = ['AmcatModel']

class AmcatModel(models.Model):
    """Replacement for standard Django-model, extending it with
    amcat-specific features."""
    __label__ = 'label'

    def _get_db_and_rq(self, rq=None):
        try:
            from amcatnavigator.utils.auth import get_request
        except:
            pass
        else: rq = get_request()
            
        return DEFAULT_DB_ALIAS if not rq else rq.user.db, rq


    ### Saving functions ###
    def save(self, using=None, **kwargs):
        dbalias, rq = self._get_db_and_rq()

        if rq is not None:
            # Check permissions for web user..
            if not self.pk and not self.__class__.can_create(rq.user):
                raise ValidationError("You're not allowed create-access on %s" % self.__class__.__name__)

            if not self.can_update(rq.user):
                raise ValidationError("You're not allowed to update %s" % self)

        super(AmcatModel, self).save(using=using or dbalias, **kwargs)

    def delete(self, using=None, **kwargs):
        dbalias, rq = self._get_db_and_rq()

        if rq is not None:
            if not self.can_delete(rq.user):
                raise ValidationError("You're not allowed to delete %s" % self)

        super(AmcatModel, self).delete(using=using or dbalias, **kwargs)


    ### Check functions ###
    def can_read(self, user):
        return True

    def can_update(self, user):
        return self.can_read(user)

    def can_delete(self, user):
        return self.can_update(user)

    @classmethod
    def can_create(cls, user):
        """Determine if `user` can create a new object"""
        return True

    class Meta():
        # https://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes
        abstract=True
        app_label = "model"

    def __unicode__(self):
        try:
            return unicode(getattr(self, self.__label__))
        except AttributeError:
            return unicode(self.id)

