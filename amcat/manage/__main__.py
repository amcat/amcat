#!/usr/bin/python

import os
import sys

if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.core.management import execute_from_command_line

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

# need to import this AFTER settings django_settings_module and importing the settings
# to prevent the import from loading the settings using the "old" DJANGO_SETTINGS_MODULE
from amcat.tools import initialize

initialize.set_signals()


execute_from_command_line(sys.argv)
#execute_manager(settings)
