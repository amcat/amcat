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
import threading
import collections

from amcat.tools.toolkit import random_alphanum

# Python 2.x vs 3.x
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

DEBUG = True

INSTALLED_APPS = ('amcat',)
    
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

SECRET_KEY = random_alphanum(30)
