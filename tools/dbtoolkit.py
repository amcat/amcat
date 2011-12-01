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

from __future__ import unicode_literals, print_function, absolute_import

import hashlib

__all__ = ['AmCATDB']

from django.db import connection, connections, transaction, DEFAULT_DB_ALIAS, utils
from django.conf import settings
from django.core.cache import cache

import logging; log = logging.getLogger(__name__)

PASSWORD_CACHE = 'amcat_password_%s'

class DatabaseError(Exception):
    pass

class UserAlreadyExists(DatabaseError):
    pass

class Database(object):
    def __init__(self, using=None):
        self.using = using or DEFAULT_DB_ALIAS
        self._cursor = None

    @property
    def cursor(self):
        if self._cursor is None:
            self._cursor = connections[self.using].cursor()
        return self._cursor

    def hash_password(self, passwd):
        """
        Return hashed password of user salted with SECRET_KEY. Hashes may differ in different
        (server) sessions, since SECRET_KEY is generated at server initialization.

        @type passwd: str, unicode
        @param passwd: raw password
        """
        hp = hashlib.sha512(passwd).hexdigest()
        return hashlib.sha512(hp+settings.SECRET_KEY).hexdigest()

    def set_password(self, user, passwd):
        """
        Set `password` for `user`.

        @type user: User
        @param user: The user for which to alter the password

        @type passwd: str, unicode

        @return None
        """
        raise NotImplementedError()

    def check_password(self, user, entered_password):
        """
        Check password for `username`.

        @param user: User object for which the password is to be checked
        @param entered_password: password as entered by user
        """
        raise NotImplementedError()

    def create_user(self, username, password):
        """
        Create user. Might throw a dbtoolkit.UserAlreadyExists exception
        when a user already exists.

        @param username: username of user
        @param password: raw password for new user
        """
        raise NotImplementedError()


class PostgreSQL(Database):
    """PostgreSQL implementation"""
    def _get_conn_params(self, user, passwd):
        db = settings.DATABASES[DEFAULT_DB_ALIAS]

        return {
            'database' : db['NAME'],
            'user' : user.username,
            'password' : passwd,
            'host' : db['HOST'],
            'port' : db['PORT']
        }

    def check_password(self, user, entered_password):
        correct_hash = cache.get(PASSWORD_CACHE % user.username)
        entered_hash = self.hash_password(entered_password)

        if correct_hash != entered_hash:
            # Wrong cache or password!
            import psycopg2

            try:
                psycopg2.connect(**self._get_conn_params(user, entered_password)).cursor()
            except:
                return False

            cache.set(PASSWORD_CACHE % user.username, entered_hash)

        return True

    def set_password(self, user, password):
        SQL = "ALTER USER %s WITH PASSWORD %s"
        md5pass = self.hash_password(user, password)

        with transaction.commit_manually(using=self.using):
            self.cursor.execute(SQL, [user.username, md5pass])
            transaction.commit()

        cache.delete(PASSWORD_CACHE % user.username)

    @transaction.commit_manually
    def create_user(self, username, password):
        SQL = "CREATE USER %s WITH PASSWORD "

        # In the SQL-statement above 'user' has to be an identifier. Unfortunately execute()
        # wraps escape-quotes around it, which results in an error.
        #
        # See: http://stackoverflow.com/questions/3382234/python-adds-e-to-string
        #
        # The regular expression checks `username` for anomalies.
        import re; ure = re.compile('^[a-zA-Z][a-zA-Z0-9_]+$')

        if not ure.match(username):
            raise ValueError("This username is not allowed!")

        try:
            SQL = (SQL % username) + " %s"
            self.cursor.execute(SQL, [password,])
        except:
            transaction.rollback(using=self.using)
            raise UserAlreadyExists()
        else:
            transaction.commit(using=self.using)

    def run_if_needed(self, sql, ok_errors=("already exists", "does not exist")):
        """Run the sql, ignoring any errors that contain an ok_error
        This *will* rollback the transaction on error to avoid the 'error state' error"""
        transaction.commit_unless_managed()
        try:
            cursor = connection.cursor()
            cursor.execute(sql)
            transaction.commit_unless_managed()
        except utils.DatabaseError, e:
            log.warn(str(e))
            for ok_error in ok_errors:
                if ok_error in str(e):
                    transaction.rollback_unless_managed()
                    return
            raise

    def create_trigger(self, table, name, code, when="AFTER",
                       actions=("INSERT","UPDATE","DELETE"), language="plpgsql"):
        """Create a trigger on the table

        This will drop the old trigger and create the language if needed.
        Because it relies on catching exceptions, the function will manage the transactions!
        """
        cursor = connection.cursor()

        # install the language if needed
        self.run_if_needed("CREATE LANGUAGE {language}".format(**locals()))

        funcname = "{name}_trigger".format(**locals())
        
        cursor.execute("""CREATE OR REPLACE FUNCTION {funcname}() RETURNS TRIGGER
                          AS $$ \n{code}\n $$ LANGUAGE {language}""".format(**locals()))

        self.run_if_needed("DROP TRIGGER {name} ON {table}".format(**locals()))

        actionsql = " OR ".join(actions)
        
        cursor.execute("""CREATE TRIGGER {name} {when} {actionsql} ON {table}
                          FOR EACH ROW EXECUTE PROCEDURE {funcname}();""".format(**locals()))

        transaction.commit_unless_managed()
            
class Sqlite(Database):
    """Sqlite implementation, does not implement user"""

    def check_password(self, user, entered_password):
        return True

    def set_password(self, user, password):
        return True

    def create_user(self, username, password):
        return True
        


VENDORS = { 'postgresql' : PostgreSQL,
            'sqlite': Sqlite,
            'dummy' : Database }

def get_database(using=DEFAULT_DB_ALIAS):
    try:
        return VENDORS[connection.vendor](using=using)
    except KeyError:
        raise DatabaseError("Your database (%s) is not supported!" % connection.vendor)

def is_postgres():
    """Is the current database postgres?"""
    return connections.databases['default']['ENGINE'] == 'django.db.backends.postgresql_psycopg2'
