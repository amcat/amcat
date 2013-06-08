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

from __future__ import unicode_literals, print_function, absolute_import

import logging
log = logging.getLogger(__name__)
import os.path

from amcat.models import AmCAT, CURRENT_DB_VERSION
from django.db import transaction, connection, connections

def execute_sql_file(filename):
    """@param filename: filename relative to tools/sql folder"""
    import amcat.tools
    fn = os.path.join(os.path.dirname(amcat.tools.__file__), "sql", filename)
    if not os.path.exists(fn):
        raise ValueError("File {fn} does not exist.".format(**locals()))
    sql = open(fn).read()
    log.info("Executing {n} bytes from {fn}".format(n=len(sql), **locals()))
    cursor = connection.cursor()
    cursor.execute(sql)
    cursor.close()

def _upgrade_from(version):
    function = "upgrade_from_{version}".format(**locals())
    if function in globals():
        globals()[function]()
    else:
        execute_sql_file("upgrade_{version}.sql".format(**locals()))

@transaction.commit_on_success
def upgrade_database():

    # create uuid extension if needed
    if connections.databases['default']["ENGINE"] == 'django.db.backends.postgresql_psycopg2':
        execute_sql_file("uuid_extension.sql")
    
    version = AmCAT.get_instance().db_version
    if version == CURRENT_DB_VERSION:
        return # early exit to avoid spurious log message

    
    while version < CURRENT_DB_VERSION:
        log.info("Upgrading from version {version}".format(**locals()))
        _upgrade_from(version)
        
        new_version = AmCAT.get_instance().db_version
        if version >= new_version:
            raise Exception("No version progress after calling upgrade ({version}>={new_version})".format(**locals()))
        version = new_version
        
    log.info("Succesfully upgraded database to version {version}".format(**locals()))
    
    
if __name__ == '__main__':
    upgrade_database()
