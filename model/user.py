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

from __future__ import unicode_literals, print_function, absolute_import
import logging; log = logging.getLogger(__name__)

from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.tools.cachable.latebind import MultiLB, LB
from amcat.tools import toolkit

from amcat.model import authorisation

def getProjectRole(db, projectid, roleid):
    return project.Project(db, projectid), authorisation.Role(db, roleid)

class Affiliation(Cachable):
    __table__ = 'affiliations'
    __idcolumn__ = 'affiliationid'
    __labelprop__ = 'name'
    
    name = DBProperty()
    users = ForeignKey(LB("User"))
    
class User(Cachable):
    __table__ = 'users'
    __idcolumn__ = 'userid'
    __labelprop__ = 'username'

    userid, username, fullname, affiliationid, active, email, languageid = DBProperties(7)
    language = DBProperty(LB("Language"))
    roles = ForeignKey(LB("Role", "authorisation"), table="users_roles")
    projects = ForeignKey(LB("Project"), table="projects_users_roles")
    projectroles = ForeignKey(MultiLB(LB("Project"), LB("Role", "authorisation")),
                              table="projects_users_roles", sequencetype=toolkit.multidict)
    
    affiliation = DBProperty(LB("Affiliation", "user"), getcolumn="affiliationid")
    
    @classmethod
    def create(cls, db, **props):
        """Custom create user method. `password` should be in the
        given properties"""
        passw = props.pop('password', None)
        if passw is None:
            raise Exception("`password` should be in `props`")
        
        db.execute_sp('create_user', (props['username'], passw))
        super(User, cls).create(db, **props)
        
    def delete(self):
        self.db.execute_sp('delete_user', (self.username,))
        super(User, self).delete(self.db)
    
    def haspriv(self, privilege, onproject=None):
        """If permission is denied, this function returns False,
        if permission granted it returns True.
        
        @type privilege: Privilege object, id, or str
        @param privilege: The requested privilege
        @param onproject: The project the privilege is requested on,
          or None (ignored) for global privileges
        
        @return: True or False (see above)"""
        try: authorisation.check(self, privilege, onproject)
        except authorisation.AccessDenied:
            return False
        
        return True
    
