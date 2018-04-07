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
import os
import datetime

from settings.tools import get_amcat_config, get_cookie_secret

amcat_config = get_amcat_config()

# Base
DEBUG = amcat_config["base"].getboolean("debug")

# Auth and security
REQUIRE_LOGON = amcat_config["auth"].getboolean("require_login")
ALLOW_REGISTER = amcat_config["auth"].getboolean("registrations")
REGISTER_REQUIRE_VALIDATION = amcat_config["auth"].getboolean("require_email")
ALLOWED_HOSTS = amcat_config["auth"].get("allowed_hosts").split(",")
SECRET_KEY = amcat_config["auth"].get("cookie_secret")

if not SECRET_KEY:
    SECRET_KEY = get_cookie_secret()

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
    INTERNAL_IPS = ['127.0.0.1']

# Database
DATABASE_OPTIONS = {
    "init_command": "set transaction isolation level read uncommitted"
}

DATABASES = {"default": {
    "ENGINE": amcat_config["database"].get("engine"),
    "NAME": amcat_config["database"].get("table"),
    "USER": amcat_config["database"].get("user"),
    "PASSWORD": amcat_config["database"].get("pass"),
    "HOST": amcat_config["database"].get("host"),
    "PORT": amcat_config["database"].get("port"),
}}

# Caching
CACHES = {
    "default": {
        "BACKEND": amcat_config['cache'].get("backend"),
        "LOCATION": amcat_config['cache'].get("location"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

CACHE_BUST_TOKEN = datetime.datetime.now().isoformat()
if not DEBUG:
    CACHE_BUST_TOKEN = amcat_config["cache"].get("bust_token")


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

    # Added manually
    '%d-%m-%Y', '%d/%m/%Y',             # '25-10-2006', '25/10/2006'
)

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
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

# List of callables that know how to import templates from various sources.
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

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': (
        os.path.join(ROOT, 'templates'),
        os.path.join(ROOT, 'amcat/scripts/query/templates')
    ),
    'OPTIONS': {
        'context_processors': (
            "django.core.context_processors.debug",
            "django.core.context_processors.i18n",
            "django.core.context_processors.media",
            "django.contrib.messages.context_processors.messages",
            "django.contrib.auth.context_processors.auth",
            "navigator.context.extra"
        ),
        'debug': DEBUG,
        'loaders': (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ),
    }
}]

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
    EMAIL_BACKEND = amcat_config["email"].get("backend")
    EMAIL_HOST = amcat_config["email"].get("host")
    EMAIL_PORT = amcat_config["email"].get("port")
    EMAIL_HOST_USER = amcat_config["email"].get("user")
    EMAIL_HOST_PASSWORD = amcat_config["email"].get("password")
    EMAIL_USE_TLS = amcat_config["email"].getboolean("use_tls")
else:
    ALLOWED_HOSTS.append("*")
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_DEFAULT_FROM = amcat_config["email"].get("from")

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
