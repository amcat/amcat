#!/usr/bin/python

import os
import os.path

from django.core.management import execute_manager
from django.db.utils import DatabaseError

#os.environ['DJANGO_SETTINGS_MODULE'] = 'amcat.settings'

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    from amcat.tools import amcatlogging, loaddata
    amcatlogging.setup()
    loaddata.set_postsync()
    execute_manager(settings)
