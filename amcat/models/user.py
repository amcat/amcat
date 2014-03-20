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
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.signals import post_save
from amcat.models.language import Language
from amcat.models.authorisation import Role, ProjectRole, ADMIN_ROLE
from amcat.models import authorisation as auth
from amcat.models.project import Project

import logging;

log = logging.getLogger(__name__)

import string, random

from django.db import models
from amcat.tools.model import AmcatModel
LITTER_USER_ID = 1


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
        ordering = ('name',)
        app_label = 'amcat'

    def can_update(self, user):
        return user.haspriv('manage_users')

class UserProfile(AmcatModel):
    """
    Additional user information is stored here
    """
    user = models.OneToOneField(User)

    affiliation = models.ForeignKey(Affiliation, default=1)
    language = models.ForeignKey(Language, default=1)
    role = models.ForeignKey(Role, default=0)

    favourite_projects = models.ManyToManyField("amcat.project", related_name="favourite_users")
    
    @property
    def projects(self):
        return Project.objects.filter(projectrole__user=self.user)

    def get_projects(self, role=None):
        """
        Get the projects for which the user has at least the role `role`. This function
        allows for guest_roles. If no role is given (or role is None), it will resolve
        to self.projects.

        @param role: role to consider
        @type role: NoneType or role.Role

        @rtype: QuerySet
        """
        if role is None:
            return self.projects

        return Project.objects.filter(
            Q(projectrole__user=self.user)|
            Q(guest_role__id__lte=role.id)
        )

    def has_role(self, role, onproject=None):
        """
        Returns whether the user has the given role. If project is given, check for a project-specific role
        If user is site-admin, always return True
        @param role: a role instance, ID, or label
        """
        if self.role_id >= ADMIN_ROLE:
            return True
            
        if isinstance(role, Role):
            role = role.id
        elif isinstance(role, (str, unicode)):
            role = Role.objects.get(label=role).id
                            
        if onproject:
            actual_role_id = onproject.get_role_id(user=self.user)
        else:
            actual_role_id = self.role_id

        log.info("{self.user.id}:{self.user.username} has role {actual_role_id} on project {onproject}, >=? {role}"
                 .format(**locals()))
        
        return actual_role_id >= role
        
    
    def haspriv(self, privilege, onproject=None):
        """
        @type privilege: Privilege object, id, or str
        @param privilege: The requested privilege
        @param onproject: The project the privilege is requested on,
          or None (ignored) for global privileges

        @return: True or False
        """
        try: auth.check(self.user, privilege, onproject)
        except auth.AccessDenied:
            return False
        return True

    def can_read(self, user):
        profile = user.get_profile()

        return (self == profile) or\
               (profile.affiliation == self.affiliation and\
                profile.haspriv("view_users_same_affiliation")) or\
               (profile.haspriv("view_users"))

    def can_update(self, user):
        profile = user.get_profile()

        return (self == profile) or\
               (profile.affiliation == self.affiliation and\
                profile.haspriv("manage_users_same_affiliation")) or\
               (profile.haspriv("manage_users"))

    def can_delete(self, user):
        return False

    def save(self, force_permissions=False, **kwargs):
        if not force_permissions:
            return super(UserProfile, self).save(**kwargs)

        # TODO / CHALLANGE: find the solution that doesn't skip a superclass
        return super(AmcatModel, self).save(**kwargs)

        

    class Meta():
        db_table = 'auth_user_profile'
        app_label = "amcat"

def create_user(username, first_name, last_name, email, affiliation, language, role,
                password=None):
        """
        Create a user with the given attributes, creating both the db user and
        the entry in the users table.

        @param password: use the given password, or a random password if None
        @return: A User object with the .password field set.
                 If the db user already existed, full_clean will raise an error
        """
        # create and validate the User object before creating the db user
        fields = dict((k, v) for (k,v) in locals().items()
                  if k in ("username","first_name", "last_name", "email"))

        # Create user
        password = password or _random_password()

        u = User.objects.create_user(username, email, password)
        u.first_name = first_name
        u.last_name = last_name
        u.save()

        # Correct profile
        prof = u.get_profile()
        prof.role = role
        prof.affiliation = affiliation
        prof.language = language
        prof.save(force_permissions=True)

        return u


def create_user_profile(sender, instance, created, **kwargs):
    """
    This function is executed when a Django User model is created.
    """
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User, dispatch_uid="create_user_profile")

def _random_password(length=8, chars=string.letters + string.digits):
    #http://code.activestate.com/recipes/59873/
    return ''.join([random.choice(chars) for i in range(length)])

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestUser(amcattest.AmCATTestCase):
    def test_create(self):
        """Test whether we can create a user"""
        u = amcattest.create_test_user()
        self.assertIsNotNone(u)
