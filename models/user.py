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

"""ORM Module representing users"""

from __future__ import print_function, absolute_import
import logging; log = logging.getLogger(__name__)
import string, random

from amcat.models.language import Language
from amcat.models import authorisation as auth

from django.db import models, DEFAULT_DB_ALIAS, connections

from amcat.tools.model import AmcatModel

from amcat.tools import dbtoolkit


class Affiliation(AmcatModel):
    """
    Model for table affiliations. Users are categorised by affiliation, and
    some permissions are granted only for ones own  affiliation
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='affiliation_id')
    name = models.CharField(max_length=200)

    class Meta():
        db_table = 'affiliations'
        ordering = ['name']
        app_label = 'amcat'

    def can_update(self, user):
        return user.haspriv('manage_users')

class User(AmcatModel):
    """
    Model for table users. Every registered AmCAT user has one entry in the users table
    """
    __label__ = 'username'

    id = models.AutoField(primary_key=True, db_column='user_id', editable=False)

    username = models.SlugField(max_length=50, unique=True, editable=False,
                                help_text="Only letters, digits and underscores are allowed.",
                                db_index=True)

    fullname = models.CharField(max_length=100, verbose_name="Full name")
    active = models.BooleanField(default=True)
    email = models.EmailField(max_length=100, unique=True)

    affiliation = models.ForeignKey(Affiliation)
    language = models.ForeignKey(Language, default=1)
    role = models.ForeignKey(auth.Role, null=False, default=0)

    def delete(self, **kwargs):
        self.active = False
        super(User, self).save(**kwargs)

    class Meta():
        db_table = 'users'
        ordering = ['username']
        app_label = 'amcat'

    @property
    def projects(self):
        """Return a sequence of all projects the current user has a role in"""
        return Project.objects.filter(projectrole__user=self)

    ### Auth ###
    def can_read(self, user):
        return (user == self or
                user.haspriv('view_users') or
                (user.affiliation == self.affiliation and
                 user.haspriv('view_users_same_affiliation')))

    def can_update(self, user):
        return (user == self or
                user.haspriv('manage_users') or
                (user.affiliation == self.affiliation and
                 user.haspriv('manage_users_same_affiliation')))

    @classmethod
    def can_create(cls, user):
        return user.haspriv('manage_users')

    ### Mimic Django-functions ###
    def set_password(self, raw_password):
        """Set the users password to raw_password"""
        if raw_password is None:
            self.active = False
        else:
            dbtoolkit.get_database().set_password(self.username, raw_password)

    def check_password(self, raw_password):
        """Returns True iff the raw_password is correct for this user"""
        return dbtoolkit.get_database().check_password(self.username, raw_password)

    def is_authenticated(self):
        """Returns True iff the current user is authenticated"""
        return True if hasattr(self, 'db') else False

    def has_perm(self, perm):
        """Returns True iff this user has this perm(ission)"""
        return self.haspriv(perm)

    def haspriv(self, privilege, onproject=None):
        """
        @type privilege: Privilege object, id, or str
        @param privilege: The requested privilege
        @param onproject: The project the privilege is requested on,
          or None (ignored) for global privileges

        @return: True or False
        """
        try: auth.check(self, privilege, onproject)
        except auth.AccessDenied:
            return False
        return True

    @property
    def is_superuser(self):
        """Returns True iff the current user is admin"""
        return (self.role.id >= auth.ADMIN_ROLE)

def current_username(using=DEFAULT_DB_ALIAS):
    return connections.databases[using]['USER']

def current_user(using=DEFAULT_DB_ALIAS):
    """Return the current user from the configured db"""
    return User.objects.get(username=current_username(using))



def create_user(username, fullname, email, affiliation, language, role=None,
                password=None, using=DEFAULT_DB_ALIAS, insert_if_db_user_exists=False):
        """
        Create a user with the given attributes, creating both the db user and
        the entry in the users table

        @param password: use the given password, or a random password if None
        @param insert_if_db_user_exists: create the User object even if the user already
                                         exists as a database user
        @return: A User object with the .password field set.
                 If the db user already existed, .password will be None
        """
        # create and validate the User object before creating the db user
        fields = {k:v for (k,v) in locals().items()
                  if k in ["username","fullname","email","affiliation","language", "role"]}
        u = User(**fields)
        u.full_clean()

        if not password: password = _random_password()
        try:
            dbtoolkit.get_database(using=using).create_user(username, password)
        except dbtoolkit.UserAlreadyExists:
            if not insert_if_db_user_exists: raise
            password = None

        # Create Django user and return with .password
        u.save()
        u.password = password
        return u

def _random_password(length=8, chars=string.letters + string.digits):
    #http://code.activestate.com/recipes/59873/
    return ''.join([random.choice(chars) for i in range(length)])

# late import to avoid cycles
from amcat.models.project import Project

if __name__ == '__main__':
    print(current_user().fullname)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestUser(amcattest.PolicyTestCase):
    def test_create(self):
        """Test whether we can create a user"""
        u = amcattest.create_test_user()
        self.assertIsNotNone(u)

    def test_current_user(self):
        u = get_current_user()
