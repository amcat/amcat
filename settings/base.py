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
from django.templatetags.static import get_static_prefix
import os
import logging; log = logging.getLogger(__name__)

from amcat.tools.toolkit import random_alphanum
from amcat.tools import hg
from os import path

# Python 2.x vs 3.x
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

if os.environ.get('DJANGO_DEBUG', None) is not None:
    DEBUG = (os.environ['DJANGO_DEBUG'] in ("1","Y", "ON"))
else:
    DEBUG = not (os.environ.get('APACHE_RUN_USER', '') == 'www-data'
                 or os.environ.get('UPSTART_JOB', '') == 'amcat_wsgi')

LOG_LEVEL = os.environ.get('DJANGO_LOG_LEVEL', 'INFO' if DEBUG else 'WARNING')
DISABLE_SENTRY = os.environ.get("DJANGO_DISABLE_SENTRY", None) in ("1","Y", "ON")

                 
LOCAL_DEVELOPMENT = not (os.environ.get('APACHE_RUN_USER', '') == 'www-data'
                         or os.environ.get('UPSTART_JOB', '') == 'amcat_wsgi')

TEMPLATE_DEBUG = DEBUG

APPNAME = 'navigator'
APPNAME_VERBOSE = 'AmCAT Navigator'

ROOT = path.abspath(path.join(path.dirname(path.abspath(__file__)), '..'))
_repo = hg.Repository(ROOT)
_tag = _repo.current_tag()
AMCAT_VERSION = (_tag[1] if _tag else None) or _repo.active_branch()

DATABASE_OPTIONS = {
   "init_command" : "set transaction isolation level read uncommitted"
}

DATABASES = dict(default=dict(
        ENGINE = os.environ.get("DJANGO_DB_ENGINE", 'django.db.backends.postgresql_psycopg2'),
        NAME = os.environ.get("DJANGO_DB_NAME", 'amcat'),
        USER =  os.environ.get("DJANGO_DB_USER", ''),           
        PASSWORD = os.environ.get("DJANGO_DB_PASSWORD", ''),           
        HOST = os.environ.get("DJANGO_DB_HOST", ''),
        PORT = os.environ.get("DJANGO_DB_PORT", ''),
    ))

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

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'navigator.utils.auth.BasicAuthenticationMiddleware',
    'navigator.utils.auth.RequireLoginMiddleware',
    'navigator.utils.auth.SetRequestContextMiddleware',
    'navigator.utils.auth.NginxRequestMethodFixMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    #'django.contrib.auth.backends.RemoteUserBackend',
)

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.SHA1PasswordHasher',
)

AUTH_PROFILE_MODULE = 'amcat.UserProfile'
LOGIN_REDIRECT_URL = "/navigator/"

ROOT_URLCONF = 'settings.urls'

TEMPLATE_DIRS = (
    os.path.join(ROOT, 'templates'),
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
    'accounts',
    'annotator',
    'navigator',
    'api',
    'debug_toolbar',
    'amcat',
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
                return open(sfile).read()
            except IOError as e:
                print("%r is not readable!" % sfile)
                raise
        else:
            print("%r is not a file." % sfile)
            raise(Exception())

    with open(sfile, 'w') as sfile:
        sfile.write(random_alphanum(40))

    return get_secret()

SECRET_KEY = get_secret()
FIXTURE_DIRS = ('../amcat', './fixtures')

REST_FRAMEWORK = {
    'PAGINATE_BY': 10,
    'PAGINATE_BY_PARAM': 'page_size', 
    'DEFAULT_PAGINATION_SERIALIZER_CLASS' : 'api.rest.serializer.AmCATPaginationSerializer',
    'DEFAULT_MODEL_SERIALIZER_CLASS' : 'api.rest.serializer.AmCATModelSerializer',
    'FILTER_BACKEND' : 'api.rest.filters.AmCATFilterBackend',
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.BrowsableAPIRenderer',
                                 'rest_framework.renderers.JSONRenderer',
                                 'api.rest.csvrenderer.CSVRenderer', ),
    
}

## SETUP LOGGER ##
if not DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", '')
    EMAIL_PORT = os.environ.get("DJANGO_EMAIL_PORT", 587)
    EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_USER", '')
    EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_PASSWORD", '')
    EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_TLS", 'Y') in ("1","Y", "ON")

    logger = logging.getLogger()

    if not DISABLE_SENTRY:
        from sentry.client.handlers import SentryHandler

        INSTALLED_APPS.append('sentry')
        INSTALLED_APPS.append('sentry.client')

        # ensure we havent already registered the handler
        if SentryHandler not in map(lambda x: x.__class__, logger.handlers):
            logger.addHandler(SentryHandler())

            # Add StreamHandler to sentry's default so you can catch missed exceptions
            logger = logging.getLogger('sentry.errors')
            logger.propagate = False
            logger.addHandler(logging.StreamHandler())

        MIDDLEWARE_CLASSES.insert(0, 'sentry.client.middleware.SentryResponseErrorIdMiddleware')

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level':LOG_LEVEL,
                'class':'logging.handlers.RotatingFileHandler',
                'filename': '/tmp/django_mainlog.log',
                'maxBytes': 1024*1024*5, # 5 MB
                'backupCount': 5,
                'formatter':'standard',
            },
            'request_handler': {
                'level':LOG_LEVEL,
                'class':'logging.handlers.RotatingFileHandler',
                'filename': '/tmp/django_requests.log',
                'maxBytes': 1024*1024*5, # 5 MB
                'backupCount': 5,
                'formatter':'standard',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': LOG_LEVEL,
                'propagate': True
            },
            'django.request': { # Stop SQL debug from logging to main logger
                'handlers': ['request_handler'],
                'level': LOG_LEVEL,
                'propagate': False
            },
        }
    }
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    # logger = logging.getLogger()
    # hdlr = logging.StreamHandler()
    # formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    # hdlr.setFormatter(formatter)
    # logger.addHandler(hdlr)
    # logger.setLevel(logging.WARNING)
    # logging.basicConfig(
        # level = logging.DEBUG,
        # format = '%(asctime)s %(levelname)s %(message)s',
    # )
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s %(name)s:%(lineno)s] %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': LOG_LEVEL,
                'class':'logging.StreamHandler',
                # 'class':'logging.handlers.RotatingFileHandler',
                # 'filename': 'logs/mylog.log',
                # 'maxBytes': 1024*1024*5, # 5 MB
                # 'backupCount': 5,
                'formatter':'standard',
            },
            'request_handler': {
                    'level': LOG_LEVEL,
                    'class':'logging.StreamHandler',
                    # 'class':'logging.handlers.RotatingFileHandler',
                    # 'filename': 'logs/django_request.log',
                    # 'maxBytes': 1024*1024*5, # 5 MB
                    # 'backupCount': 5,
                    'formatter':'standard',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': LOG_LEVEL,
                'propagate': True
            },
            'django.request': { # Stop SQL debug from logging to main logger
                'handlers': ['request_handler'],
                'level': LOG_LEVEL,
                'propagate': False
            },
        }
    }



