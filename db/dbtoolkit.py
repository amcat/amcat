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

"""Database abstraction layer"""

import md5

__all__ = ['AmCATDB']

from django.db import connection, transaction

class DatabaseError(Exception):
    pass

class Database(object):
    """"""
    def __init__(self, user, passwd):
        self.cursor = connection.cursor()

    def set_password(self, username, passwd):
        """
        Set `password` for `user`.

        @type user: str
        @param user: or 'rolname' for some databases

        @type passwd: str, unicode

        @return None
        """
        pass

    def check_password(self, username, encr_pass, raw_pass):
        """
        Check password for `username`.

        @param encr_pass: hashed (+salted) password stored in database
        @param raw_pass: raw password given by user
        """
        pass

    def create_user(self, username, password):
        """
        Create user.

        @param username: username of user
        @param password: raw password for new user
        """
        pass

class PostgreSQL(Database):
    """PostgreSQL implementation"""
    def _get_hash(self, username, passwd):
        return 'md5' + md5.new(passwd+username).hexdigest()

    def set_password(self, username, passwd):
        SQL = "UPDATE pg_authid SET rolpassword=%s WHERE rolname=%s"
        hash = self._get_hash(username, passwd)
        cursor.execute(SQL, [hash, username])

    def check_password(self, username, encr_pass, raw_pass):
        return raw_pass == self._get_hash(username, encr_pass)

    def create_user(self, username, password):
        SQL = "CREATE USER %s WITH PASSWORD %s"
        cursor.execute(SQL, [username, password])

    def delete_user(self, username):
        cursor.execute("DROP USER %s", [username])




VENDORS = { 'postgresql' : PostgreSQL,
            'dummy' : Database }

try:
    AmCATDB = VENDORS.get(connection.vendor, None)
except TypeError:
    raise(DatabaseError("Your database (%s) is not supported!" % connection.vendor))