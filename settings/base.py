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
from os import path

import datetime

from amcat import __version__
from amcat.tools.toolkit import random_alphanum

# Python 2.x vs 3.x
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

if os.environ.get('AMCAT_DEBUG', None) is not None:
    DEBUG = (os.environ['AMCAT_DEBUG'] in ("1", "Y", "ON"))
else:
    DEBUG = not (os.environ.get('APACHE_RUN_USER', '') == 'www-data'
                 or os.environ.get('UPSTART_JOB', '') == 'amcat_wsgi')

LOCAL_DEVELOPMENT = not (os.environ.get('APACHE_RUN_USER', '') == 'www-data'
                         or os.environ.get('UPSTART_JOB', '') == 'amcat_wsgi')

TEMPLATE_DEBUG = DEBUG

APPNAME = 'navigator'
APPNAME_VERBOSE = 'AmCAT Navigator'
AMCAT_VERSION = __version__

REQUIRE_LOGON = os.environ.get('AMCAT_REQUIRE_LOGON', 'Y').lower() in ("1", "y", "t")
ALLOW_REGISTER = os.environ.get('AMCAT_ALLOW_REGISTER', 'Y').lower() in ("1", "y", "t")

REGISTER_REQUIRE_VALIDATION = os.environ.get('AMCAT_REGISTER_REQUIRE_VALIDATION', 'Y').lower() in ("1", "y", "t")
ROOT = path.abspath(path.join(path.dirname(path.abspath(__file__)), '..'))

DATABASE_OPTIONS = {
    "init_command": "set transaction isolation level read uncommitted"
}

ALLOWED_HOSTS = os.environ.get("AMCAT_ALLOWED_HOSTS", "localhost,.amcat.nl,.vu.nl").split(",")

ACCESS_CONTROL_ORIGINS = []
ACCESS_CONTROL_HEADERS = []

if DEBUG:
    ACCESS_CONTROL_METHODS = ["GET", "POST"]
    ACCESS_CONTROL_ORIGINS = ["*"]
    ACCESS_CONTROL_HEADERS = [
        "Accept", "Accept-Encoding", "Accept-Language", "Access-Control-Request-Headers",
        "Access-Control-Request-Method", "Connection", "Host", "Origin", "User-Agent",
        "X-CSRFTOKEN", "X-HTTP-METHOD-OVERRIDE"
    ]

DATABASES = dict(default=dict(
    ENGINE=os.environ.get("AMCAT_DB_ENGINE", 'django.db.backends.postgresql_psycopg2'),
    NAME=os.environ.get("AMCAT_DB_NAME", 'amcat'),
    USER=os.environ.get("AMCAT_DB_USER", ''),
    PASSWORD=os.environ.get("AMCAT_DB_PASSWORD", ''),
    HOST=os.environ.get("AMCAT_DB_HOST", ''),
    PORT=os.environ.get("AMCAT_DB_PORT", ''),
))


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

CACHE_BUST_TOKEN = datetime.datetime.now().isoformat()
if not DEBUG:
    CACHE_BUST_TOKEN = os.environ.get("CACHE_BUST_TOKEN", CACHE_BUST_TOKEN)


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Amsterdam'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Accept a range of date formats in forms
DATE_INPUT_FORMATS = (
    # Defaults
    '%Y-%m-%d', '%Y/%m/%d',             # '2006-10-25', '2006/10/25'
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'

    # Added manually
    '%d-%m-%Y', '%d/%m/%Y',             # '25-10-2006', '25/10/2006'
)

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(ROOT, 'navigator', 'media')
STATIC_ROOT = os.path.join(MEDIA_ROOT, 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'
STATIC_URL = '/media/static/'
ACCOUNTS_URL = "/accounts/"
API_URL = '/api/'

STATICFILES_DIRS = (
    # Explicit paths make PyCharm pick up on it.
    os.path.join(ROOT, "annotator/static"),
    os.path.join(ROOT, "navigator/static"),
    os.path.join(ROOT, "static"),
)

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

#TEST_RUNNER = "django.test.runner.DiscoverRunner"
TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = [
    'django.middleware.csrf.CsrfViewMiddleware',
    'navigator.utils.misc.MethodOverrideMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'navigator.utils.maintenance.MaintenanceModeMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'navigator.utils.auth.RequireLoginMiddleware',
    'navigator.utils.auth.SetRequestContextMiddleware',
    'navigator.utils.auth.NginxRequestMethodFixMiddleware',
    'navigator.utils.auth.HTTPAccessControl',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    #'django.contrib.auth.backends.RemoteUserBackend',
)

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
)

AUTH_PROFILE_MODULE = 'amcat.UserProfile'
LOGIN_REDIRECT_URL = "/"

ROOT_URLCONF = 'settings.urls'

TEMPLATE_DIRS = (
    os.path.join(ROOT, 'templates'),
    os.path.join(ROOT, 'amcat/scripts/query/templates')
)

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'accounts',
    'annotator',
    'navigator',
    'api',
    'amcat',
    "django_extensions",
    'djcelery',
    "formtools"
]

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.contrib.messages.context_processors.messages",
    "django.contrib.auth.context_processors.auth",
    "navigator.context.extra"
)

DEFAULT_FROM_EMAIL = "wat200@vu.nl"


def get_secret():
    """
    Get or create a secret key to sign cookies with.

    ~/.cookie-secret will be used to store the secret key.
    """
    sfile = os.path.expanduser("~/.cookie-secret")

    if os.path.exists(sfile):
        if os.path.isfile(sfile):
            try:
                with open(sfile) as f:
                    return f.read()
            except IOError as e:
                print("%r is not readable!" % sfile)
                raise
        else:
            print("%r is not a file." % sfile)
            raise (Exception())

    with open(sfile, 'w') as sfile:
        sfile.write(random_alphanum(40))

    return get_secret()


SECRET_KEY = get_secret()
FIXTURE_DIRS = (os.path.join(ROOT, "amcat/models"),)

REST_FRAMEWORK = {
    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'api.rest.pagination.AmCATPageNumberPagination',
    'DEFAULT_METADATA_CLASS': 'api.rest.metadata.AmCATMetadata',

    # Filtering / models
    'ORDERING_PARAM': 'order_by',
    'SEARCH_PARAM': 'search',
    'DEFAULT_SERIALIZER_CLASS': 'api.rest.serializer.AmCATModelSerializer',
    'DEFAULT_FILTER_BACKENDS': (
        'api.rest.filters.DjangoPrimaryKeyFilterBackend',
        'api.rest.filters.MappingOrderingFilter',
        'rest_framework.filters.SearchFilter',
    ),

    # Rendering
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework.renderers.JSONRenderer',
        'api.rest.tablerenderer.CSVRenderer',
        'api.rest.tablerenderer.XLSXRenderer',
        'api.rest.tablerenderer.SPSSRenderer',
        'api.rest.tablerenderer.XHTMLRenderer',
        'api.rest.tablerenderer.RdaRenderer',
    ),

    # Auth
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'api.rest.tokenauth.ExpiringTokenAuthentication',
    ),
    'EXCEPTION_HANDLER': 'api.rest.exception.exception_handler',
}

if not DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get("AMCAT_EMAIL_HOST", '')
    EMAIL_PORT = os.environ.get("AMCAT_EMAIL_PORT", 587)
    EMAIL_HOST_USER = os.environ.get("AMCAT_EMAIL_USER", '')
    EMAIL_HOST_PASSWORD = os.environ.get("AMCAT_EMAIL_PASSWORD", '')
    EMAIL_USE_TLS = os.environ.get("AMCAT_EMAIL_TLS", 'Y') in ("1", "Y", "ON")

else:
    ALLOWED_HOSTS.append("*")
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Pnotify is a javascript library to show (unintrusive) popups
PNOTIFY_DEFAULTS = {
    "type": "info",
    "delay": 1000,
    "nonblock": {
        "nonblock": True,
        "nonblock_opacity": .2
    }
}

# User roles available when signing up
MAX_SIGNUP_ROLEID = int(os.environ.get("AMCAT_MAX_SIGNUP_ROLEID", 0))  # reader