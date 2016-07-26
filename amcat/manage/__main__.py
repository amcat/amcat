#!/usr/bin/python

import os
import sys

# manage is not in the project root, so we need to insert the cwd to the path
sys.path.insert(0, '')

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
