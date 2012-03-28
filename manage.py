#!/usr/bin/python
from django.core.management import execute_manager
from django.db.models.signals import post_syncdb
from django.db import connection, transaction
from django.db.utils import DatabaseError

import amcat.models
from amcat.tools import dbtoolkit
    
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)


def postsync(sender, **kwargs):
    if dbtoolkit.is_postgres():
        print "Performing post-syncdb operations"
        set_permissions()
    else:
        print "Skipping post-syncdb for non-postgres db"
    
def set_permissions():
    print "Setting permissions on tables"
    cursor = connection.cursor()
    cursor.execute("select tablename from pg_tables where schemaname in ('public');")
    for tabname in cursor.fetchall():
        cursor.execute("GRANT ALL ON %s TO public" % tabname)
    print "Setting permissions on sequences"
    cursor = connection.cursor()
    cursor.execute("SELECT relname FROM pg_class WHERE relkind = 'S';")
    for relname in cursor.fetchall():
        cursor.execute("GRANT ALL ON %s TO public" % relname)
    transaction.commit_unless_managed()


post_syncdb.connect(postsync, sender=amcat.models)
    
if __name__ == "__main__":
    from amcat.tools import amcatlogging
    amcatlogging.setup()
    execute_manager(settings)
