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

"""
Unparametrized entry point for the AmCAT system

The System singleton contains 'foreign key' relations to the top
level AmCAT objects such as projects, users, and analyses.
"""

from cachable2 import Cachable, DBProperty, ForeignKey, DBProperties
import project, user, authorisation, analysis
from toolkit import deprecated

from annotationschema import AnnotationSchema#, AnnotationSchemaFieldtype

class System(Cachable):
    """Cachable without id that provides access to top level AmCAT objects"""
    __table__ = None
    __idcolumn__ = None


    # Annotationschema-properties
    annotationschemas = ForeignKey(lambda : AnnotationSchema, table="annotationschemas")
    #annotationschemafieldtypes = ForeignKey(lambda : AnnotationSchemaFieldtype, table="annotationschemas_fieldtypes")
        
    def __init__(self, db, id=None):
        Cachable.__init__(self, db, ())
        
    def getUserByUsername(self, uname):
        """Search for a user given a username"""
        #cacheMultiple(self.users, ["username", ])
        
        for usr in self.users:
            if usr.username == uname:
                return usr

    @property
    @deprecated
    def users(self):
        return user.User.all(self.db)
    @property
    @deprecated
    def projects(self):
        return project.Project.all(self.db)
    @property
    @deprecated
    def analyses(self):
        return analysis.Analysis.all(self.db)
    @property
    @deprecated
    def roles(self):
        return authorisation.Role.all(self.db)
    @property
    @deprecated
    def privileges(self):
        return authorisation.Privilege.all(self.db)
    @property
    @deprecated
    def annotationschemas(self):
        return AnnotationSchema.all(self.db)
    @property
    @deprecated
    def annotationschemafieldtypes(self):
        return AnnotationSchemaFieldtype.all(self.db)
    
if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True)
    print "Querying System object"
    system = System(db, ())
    print system.projects
    u = list(system.users)
    db.printProfile()

    print "Querying second system object"
    system2 = System(db, ())
    s = system.projects
    u = system.users
    db.printProfile()
