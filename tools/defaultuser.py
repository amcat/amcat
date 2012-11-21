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

"""
Code which creates a superuser account (amcat:amcat) when syncdb is
called.
"""

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.contrib.auth.management import create_superuser
from django.db.models import signals

from amcat.models.authorisation import Role

# From http://stackoverflow.com/questions/1466827/ --
#
# Prevent interactive question about wanting a superuser created.  (This code
# has to go in this otherwise empty "models" module so that it gets processed by
# the "syncdb" command during database creation.)
signals.post_syncdb.disconnect(
    create_superuser,
    sender=auth_models,
    dispatch_uid='django.contrib.auth.management.create_superuser'
)


# Create our own default user automatically.
def create_testuser(app, created_models, verbosity, **kwargs):
  try:
    auth_models.User.objects.get(username='amcat')
  except auth_models.User.DoesNotExist:
    su = auth_models.User.objects.create_superuser('amcat', 'amcat@example.com', 'amcat')
    sup = su.get_profile()
    sup.role = Role.objects.get(label="superadmin", projectlevel=False)
    sup.save()
    print("A default superuser `amcat` with password `amcat` has been created.")
  else:
    pass

signals.post_syncdb.connect(create_testuser,
    sender=auth_models, dispatch_uid='common.models.create_defaultuser')

