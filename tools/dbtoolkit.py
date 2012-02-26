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

"""Module to supply database-specific operations needed by AmCAT"""

from __future__ import unicode_literals, print_function, absolute_import

import hashlib, re
from contextlib import contextmanager

from django.db import connection, connections, transaction, DEFAULT_DB_ALIAS
from django.db.utils import DatabaseError
from django.conf import settings
from django.core.cache import cache

import logging; log = logging.getLogger(__name__)

PASSWORD_CACHE = 'amcat_password_{username}'

class UserAlreadyExists(DatabaseError):
    """User already exists in the database"""
    pass

class Database(object):
    """Base class for database-specific functions needed by AmCAT""" 
    
    def __init__(self, using=None):
        self.using = using or DEFAULT_DB_ALIAS
        self._cursor = None

    @property
    def cursor(self):
        """Get a cursor on the database.
        This is a shared cursor, so beware of rollbacks and multithreading
        """
        
        if self._cursor is None:
            self._cursor = connections[self.using].cursor()
        return self._cursor


    def set_password(self, username, passwd):
        """
        Set the password for the given user.
        Passes silently for databases without authorisation
        """
        raise NotImplementedError()

    def check_password(self, username, entered_password):
        """
        Check password for `username`.
        Returns True if the password matches or if the database does not support authorisation
        """
        raise NotImplementedError()

    def create_user(self, username, password):
        """
        Create user. Might throw a dbtoolkit.UserAlreadyExists exception
        when a user already exists.
        """
        raise NotImplementedError()


    def delete_user(self, username):
        """
        Delete the user user. Use with care :-)
        """
        raise NotImplementedError()

    def user_exists(self, username):
	"""
	Does the user exist?
	"""
	raise NotImplementedError()

    
class PostgreSQL(Database):
    """PostgreSQL implementation"""
    
    def _get_conn_params(self, username, passwd):
        """Get the keyword arguments needed to connect to the db"""
        db = settings.DATABASES[DEFAULT_DB_ALIAS]
        #passwd = "'%s'" % re.escape(passwd)
        return {
            'database' : db['NAME'],
            'user' : username,
            'password' : passwd,
            'host' : db['HOST'],
            'port' : db['PORT']
        }

    def check_password(self, username, entered_password):
        import psycopg2 # lazy import to prevent global dependency
        username = self.check_username(username)
        correct_hash = cache.get(PASSWORD_CACHE.format(**locals()))
        entered_hash = hash_password(entered_password)

        if correct_hash == entered_hash: return True
        
        # Password does not match cache (which might not exist). --> try logging in
        try:
            params = self._get_conn_params(username, entered_password)
            psycopg2.connect(**params).cursor()
            cache.set(PASSWORD_CACHE.format(**locals()), entered_hash)
            return True
        except psycopg2.OperationalError, e:
            if "password authentication failed" in str(e):
                return False
            raise

    def set_password(self, username, password):
        username = self.check_username(username)
        SQL = "ALTER USER {username} WITH PASSWORD %s".format(username=username)

        with transaction.commit_manually(using=self.using):
            self.cursor.execute(SQL, [password])
            transaction.commit(using=self.using)

        cache.delete(PASSWORD_CACHE.format(**locals()))

    @transaction.commit_manually
    def create_user(self, username, password):
        username = self.check_username(username)
        SQL = "CREATE USER {username} WITH PASSWORD %s".format(**locals())
        
        try:
            self.execute_transaction(SQL, password, use_savepoint=False)
        except DatabaseError, e:
            if "already exists" in str(e):
                raise UserAlreadyExists()
            else:
                raise


    @transaction.commit_manually
    def delete_user(self, username):
        username = self.check_username(username) 
        SQL = "DROP  USER IF EXISTS {username}".format(**locals())
        self.execute_transaction(SQL, use_savepoint=False)

    def user_exists(self, username):
	SQL = "SELECT usename FROM pg_catalog.pg_user WHERE usename=%s"
	cursor = connection.cursor()
	cursor.execute(SQL, [username])
	return bool(cursor.fetchone())
    
	
        
    def run_if_needed(self, sql, ok_errors=("already exists", "does not exist")):
        """Run the sql, ignoring any errors that contain an ok_error
        This *will* rollback the transaction on error to avoid the 'error state' error"""
        transaction.commit_unless_managed()
        try:
            cursor = connection.cursor()
            cursor.execute(sql)
            transaction.commit_unless_managed()
        except DatabaseError, e:
            log.debug(str(e))
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

    
    def check_username(self, username):
        """Postgres usernames are identifiers, this means that
        1) They cannot be passed as SQL arguments, so we need to do string formatting ourselves,
           so we must check them to prevent injection
        2) They are case insensitive (!), so we will lower them

        @return the lowercase username, or raise a ValueError
        
        See also: http://stackoverflow.com/questions/3382234/python-adds-e-to-string
        """
        username = username.lower()
        if not re.match('^[a-z][a-z0-9_]+$', username):
            raise ValueError("This username is not allowed!")
        return username

    @contextmanager
    def transaction(self, use_savepoint=True):
        """Context manager for wrapping code in a (savepoint) transaction)"""
        if use_savepoint: sid = transaction.savepoint()
        try:
            yield
        except:
            if use_savepoint:
                transaction.savepoint_rollback(sid)
            else:
                transaction.rollback()
            raise
        else:
            if use_savepoint:
                transaction.savepoint_commit(sid)
            else:
                transaction.commit()
    
    def execute_transaction(self, sql, *sqlarguments, **kargs):
        """Execute sql within a transaction.
        Extra arguments are passed to the transaction context manager"""
        cursor = self.cursor
        with self.transaction(**kargs):
            log.debug("EXECUTING {sql} ({sqlarguments})".format(**locals()))
            cursor.execute(sql, sqlarguments)
        
class Sqlite(Database):
    """Sqlite implementation, passes silently on authorisation methods"""

    def check_password(self, username, entered_password):
        return True

    def set_password(self, username, password):
        pass

    def create_user(self, username, password):
        pass
        
    def delete_user(self, username):
        pass

def hash_password(passwd):
    """
    Return hashed password of user salted with SECRET_KEY. Hashes may differ in different
    (server) sessions, since SECRET_KEY is generated at server initialization.
    """
    hp = hashlib.sha512(passwd).hexdigest()
    return hashlib.sha512(hp+settings.SECRET_KEY).hexdigest()
    

VENDORS = { 'postgresql' : PostgreSQL,
            'sqlite': Sqlite,
            'dummy' : Database }

def get_database(using=DEFAULT_DB_ALIAS):
    """Get a database object for this session"""
    try:
        return VENDORS[connection.vendor](using=using)
    except KeyError:
        raise DatabaseError("Your database (%s) is not supported!" % connection.vendor)

def is_postgres():
    """Is the current database postgres?"""
    return connections.databases['default']['ENGINE'] == 'django.db.backends.postgresql_psycopg2'



###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest
from amcat.tools import amcatlogging; amcatlogging.infoModule()

class TestDBToolkit(amcattest.PolicyTestCase):

    PYLINT_IGNORE_EXTRA = ("W0612", "W0613", # unused arg/var string format false positive
                           "W0703", # catch exception
                           "W0231", "W0221", # for dummy methods in external call
                           )
    def x_test_users_passwords(self):
        """Create u new user, set its password, check, change password, check"""
        # Lijkt niet te werken vanuit django testing, maar wel als (django) standalone :-(
        username = 'TestDBToolkit_test_users_passwords_testuser'
        password = b'pass123'
        log.info("Creating user {username} with password {password}".format(**locals()))
        db = get_database()

        try:
            try:
                db.create_user(username, password)
            except UserAlreadyExists:
                log.info("Test user existed, ignoring")

            self.assertTrue(db.check_password(username, password))
            self.assertFalse(db.check_password(username, "wrong_password"))

	    self.assertTrue(db.user_exists(username))

            password2 = "!@$!%$^^%'&&%^4*&^"
            db.set_password(username, password2)
            self.assertTrue(db.check_password(username, password2))
            self.assertFalse(db.check_password(username, password))
        finally:
            try:

                db.delete_user(username)
            except Exception, e:
                log.error(e)
                import traceback
                traceback.print_exc()

	self.assertFalse(db.user_exists(username))
	
def run_test():
    """
    for some reason, django testing gets in the way of creating users
    (the call succeeds, but can't log on with the credentials)
    running the same code from the command line does work
    this might be connected with http://code.google.com/p/amcat/issues/detail?id=49
    run with python -c "from amcat.tools import dbtoolkit; dbtoolkit.run_test()"
    """
    from amcat.tools.amcatlogging import setup; setup()

    class Dummy(TestDBToolkit):
        """Dummy class for testing externally"""
        def __init__(self):pass
        def assertTrue(self, test):
            if not test:
                raise Exception("%r is not True" % test)
        def assertFalse(self, test):
	    self.assertTrue(not test)
                
    TestDBToolkit.x_test_users_passwords(Dummy())


if __name__ == '__main__':
    run_test()
