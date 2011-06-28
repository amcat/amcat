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
from amcat.model.authorisation import Role, ProjectRole

from django.db import models

#def getProjectRole(db, projectid, roleid):
#    return project.Project(db, projectid), authorisation.Role(db, roleid)

class Affiliation(models.Model):
    id = models.IntegerField(primary_key=True, db_column='affiliation_id')
    name = models.CharField(max_length=200)
    
    def __unicode__(self):
        return self.name

    class Meta():
        db_table = 'affiliations'
        app_label = 'models'
    
    
class User(models.Model):
    id = models.IntegerField(primary_key=True, db_column='user_id')

    username = models.CharField(max_length=50)
    fullname = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    email = models.EmailField(max_length=100)

    affiliation = models.ForeignKey(Affiliation)
    language = models.ForeignKey(Language)
    #projects = models.ManyToManyField(Project, db_table="projects_users_roles")
    roles = models.ManyToManyField(Role, db_table="users_roles")
    #p_roles = models.ManyToManyField(ProjectRole)
    
    def __unicode__(self):
        return self.username

    class Meta():
        db_table = 'users'
        app_label = 'models'
    
    @property
    def projects(self):
        return (r.project for r in self.projectrole_set.all())

    #@classmethod
    #def create(cls, db, **props):
    #    """Custom create user method. `password` should be in the
    #    given properties"""
    #    passw = props.pop('password', None)
    #    if passw is None:
    #        raise Exception("`password` should be in `props`")
    #    
    #    db.execute_sp('create_user', (props['username'], passw))
    #    super(User, cls).create(db, **props)
        
    #def delete(self):
    #    self.db.execute_sp('delete_user', (self.username,))
    #    super(User, self).delete(self.db)
    
    #def haspriv(self, privilege, onproject=None):
    #    """If permission is denied, this function returns False,
    #    if permission granted it returns True.
    #    
    #    @type privilege: Privilege object, id, or str
    #    @param privilege: The requested privilege
    #    @param onproject: The project the privilege is requested on,
    #      or None (ignored) for global privileges
    #    
    #    @return: True or False (see above)"""
    #    try: authorisation.check(self, privilege, onproject)
    #    except authorisation.AccessDenied:
    #        return False
    #    
    #    return True
    
