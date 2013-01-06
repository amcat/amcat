#!/usr/bin/python
from django.core.management import execute_manager
from django.core import management


import os
import os.path

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

# need to import this AFTER settings django_settings_module and importing the settings
# to prevent the import from loading the settings using the "old" DJANGO_SETTINGS_MODULE
from amcat.tools import initialize

if __name__ == "__main__":
    initialize.set_signals()

    import sys
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
    #execute_manager(settings)
