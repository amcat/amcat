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

from cachable import Cachable, DBFKPropertyFactory, CachingMeta, cacheMultiple
import project
import user
import analysis
from annotationschema import AnnotationSchema, AnnotationSchemaFieldtype

class System(Cachable):
    """Cachable without id that provides access to top level AmCAT objects"""
    __metaclass__ = CachingMeta
    __table__ = None
    __idcolumn__ = None

    projects = DBFKPropertyFactory("projects", "projectid",
                                   dbfunc=project.Project)
    users = DBFKPropertyFactory("users", "userid", dbfunc=user.User)
    analyses = DBFKPropertyFactory("parses_analyses", "analysisid",
                                   dbfunc=analysis.Analysis)

    annotationschemas = DBFKPropertyFactory("annotationschemas", "annotationschemaid", dbfunc=AnnotationSchema)
    fieldtypes = DBFKPropertyFactory("annotationschemas_fieldtypes", "fieldtypeid", dbfunc=AnnotationSchemaFieldtype)

    def __init__(self, db, id=None):
        Cachable.__init__(self, db, ())
        
    @property
    def schematypes(self):
        # Seems to be hardcoded (i.e. not stored in table)
        res = []
        for (i, label) in enumerate(('Net', 'Simple')):
            res.append(Schematype(i, label))
        return res
    
    def getUserByUsername(self, uname):
        """Search for a user given a username"""
        cacheMultiple(self.users, ["username", ])
        
        for usr in self.users:
            if usr.username == uname:
                return usr

        
class Schematype(object):
    def __init__(self, id, label):
        self.id = id
        self.label = label

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
