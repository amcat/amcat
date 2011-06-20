# Django settings for amcatnavigator project.
import os

# Python 2.x vs 3.x
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

DEBUG = True

INSTALLED_APPS = ('amcat.model',)
    
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