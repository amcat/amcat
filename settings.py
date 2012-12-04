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

# Django settings for amcatnavigator project.
import os

from amcat.tools.toolkit import random_alphanum

# Python 2.x vs 3.x
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

DEBUG = True

INSTALLED_APPS = (
    'amcat',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    )
AUTH_PROFILE_MODULE = 'amcat.UserProfile'

#TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
#NOSE_ARGS = ['--with-progressive','--pdb']

TIME_ZONE = 'Europe/Amsterdam'

DATABASES = dict(default=dict(
        ENGINE = os.environ.get("DJANGO_DB_ENGINE", 'django.db.backends.postgresql_psycopg2'),
        NAME = os.environ.get("DJANGO_DB_NAME", 'amcat'),
        USER =  os.environ.get("DJANGO_DB_USER", ''),           
        PASSWORD = os.environ.get("DJANGO_DB_PASSWORD", ''),           
        HOST = os.environ.get("DJANGO_DB_HOST", ''),
        PORT = ''
    ))

SECRET_KEY = random_alphanum(30)

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    
)
