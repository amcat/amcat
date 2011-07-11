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

from amcat.tools import toolkit
from amcat.model.language import Language
from amcat.model.project import Project
from amcat.model import authorisation as auth

from django.contrib.auth.models import get_hexdigest, check_password
from django.db import models

from amcat.tools.model import AmcatModel

from amcat.db import dbtoolkit

import md5

PASS_ALGORITHM = 'sha1'

#def getProjectRole(db, projectid, roleid):
#    return project.Project(db, projectid), authorisation.Role(db, roleid)

class Affiliation(AmcatModel):
    id = models.IntegerField(primary_key=True, db_column='affiliation_id')
    name = models.CharField(max_length=200)
    
    def __unicode__(self):
        return self.name

    class Meta():
        db_table = 'affiliations'   
        ordering = ['name']

class User(AmcatModel):
    id = models.IntegerField(primary_key=True, db_column='user_id', editable=False)

    username = models.SlugField(max_length=50, unique=True,
                                help_text="Only letters, digits and underscores are allowed.")

    fullname = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    email = models.EmailField(max_length=100)

    affiliation = models.ForeignKey(Affiliation)
    language = models.ForeignKey(Language, default=1)
    roles = models.ManyToManyField(auth.Role, db_table="users_roles")

    password = models.CharField(max_length=128, help_text="[algo]$[salt]$[hexdigest]. Please do not edit directly.")
    
    def __unicode__(self):
        return self.username

    class Meta():
        db_table = 'users'
        ordering = ['username']
    
    @property
    def projects(self):
        return Project.objects.filter(projectrole__user=self)

    #@property
    #def password(self):
    #    """
    #    None if no password is set.
    #
    #    If the password is encrypted, this property will contain the string md5
    #    followed by a 32-character hexadecimal MD5 hash. The MD5 hash will be of
    #    the user's password concatenated to their username (for example, if user
    #    joe has password xyzzy, PostgreSQL will store the md5 hash of xyzzyjoe).
    #    """
    #    return self.password

    ### Auth ###
    def can_read(self, user):
        return (user == self or user.haspriv('view_all_users'))

    def can_update(self, user):
        return (user == self or user.haspriv('update_user'))

    ### Mimic Django-functions ###
    def set_password(self, raw_password):
        if raw_password is None:
            self.active = False
            self.password = None
        else:
            pass

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    ### Custom ###
    def get_roles(self, project=None):
        if project is None:
            return self.roles.all()
        return (r.role for r in self.projectrole_set.all() if r.project==project)

        # Alternatively (if above is too slow):
        # return (r.role for r in auth.ProjectRole.objects.filter(project=project, user=user))

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
