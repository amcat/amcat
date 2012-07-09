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
from django.core import cache

from django.db import models
from django.core.exceptions import ValidationError
from amcat.tools.caching import _get_cache_key

__all__ = ['AmcatModel']

class AmcatModel(models.Model):
    """Replacement for standard Django-model, extending it with
    amcat-specific features."""
    __label__ = 'label'

    def _get_rq(self):
        """
        If amcatnavigator is running, see if we can get a request
        object, with which we check for permissions

        @return: request object or None
        """
        try:
            from amcatnavigator.utils.auth import get_request
        except:
            pass
        else:
            return get_request()


    ### Saving functions ###
    def save(self, **kwargs):
        rq = self._get_rq()

        if rq is not None:
            # Check permissions for web user..
            if not self.pk:
                if not self.__class__.can_create(rq.user):
                    raise ValidationError("You're not allowed create-access on %s"
                                          % self.__class__.__name__)
            elif not self.can_update(rq.user):
                raise ValidationError("You're not allowed to update %s" % self)

        # Invalidate cache
        cache.delete(_get_cache_key(self, self.id))

        super(AmcatModel, self).save(**kwargs)

    def delete(self, **kwargs):
        rq = self._get_rq()

        if rq is not None:
            if not self.can_delete(rq.user):
                raise ValidationError("You're not allowed to delete %s" % self)

        # Invalidate cache
        cache.delete(_get_cache_key(self, self.id))

        super(AmcatModel, self).delete(**kwargs)


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

    
