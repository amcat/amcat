# Django settings for amcatnavigator project.
import os

# Python 2.x vs 3.x
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
    
DEBUG = True
LOCAL_DEVELOPMENT = True
TEMPLATE_DEBUG = DEBUG

APPNAME = 'amcatnavigator'

ROOT = os.path.dirname(os.path.abspath(__file__))

ADMINS = (
    ('Martijn Bastiaan', 'martijn.bastiaan@gmail.com'),
    ('Wouter van Atteveldt', 'wouter@vanatteveldt.com'),
    ('Jouke Jacobi', 'joukejacobi@gmail.com')
)

MANAGERS = ADMINS

# http://docs.djangoproject.com/en/dev/topics/auth/#storing-additional-information-about-users
AUTH_PROFILE_MODULE = 'general.UserProfile'

# Databases / Caches are defined in ~/.amcatrc3. Example file:
# 
# [db-default]
# name=amcat
# engine=django.db.backends.postgresql_psycopg2
# user=apache
# password=secret
# host=localhost
# port=5432
#
# [caching-default]
# backend=django.core.cache.backends.memcached.MemcachedCache
# location=127.0.0.1:11211

def sections(identifier):
    c = configparser.ConfigParser()
    c.readfp(file(os.path.expanduser('~/.amcatrc3')))
    
    for sect in c.sections():
        db = sect.split('-')        
        if db[0] == identifier and len(db) is 2:
            yield db[1], c.items(sect)
            
def filldict(vals, dic):
    for id, opts in vals:
        dic[id] = {}
        for k,v in opts:
            dic[id][k.upper()] = v
    return dic
   
DATABASES = filldict(sections('db'), dict())
CACHES = filldict(sections('caching'), dict())

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
MEDIA_ROOT = os.path.join(ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '(-g4ascorqa3h4lk8sdh%2_s!r0vt*50)7%7+k27*+l=ku1u64'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware'
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.RemoteUserBackend',
)

ROOT_URLCONF = 'amcatnavigator.urls'

TEMPLATE_DIRS = ()

INSTALLED_APPS = ()

TEMPLATE_CONTEXT_PROCESSORS = ()

