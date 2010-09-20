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

from cachable import Cachable, DBPropertyFactory, ForeignKey
import permissions
from functools import partial
import user, article, project

class Batch(Cachable):
    __table__ = 'batches'
    __idcolumn__ = 'batchid'
    __dbproperties__ = ["name", "insertDate", "query"]
    insertUser = DBPropertyFactory("insertuserid", factory = lambda : user.User)
    project = DBPropertyFactory("projectid", factory = lambda : project.Project)
    articles = ForeignKey(lambda:article.Article)
    def __init__(self, *args, **kargs):
        Cachable.__init__(self, *args, **kargs)
        
def createBatch(project, name, query, db=None):
    if db is None: db = project.db
    if type(project) <> int: project = project.id
    batchid = db.insert('batches', dict(name=name, projectid=project, query=query))
    return Batch(db, batchid)
                        

if __name__ == '__main__':
    import dbtoolkit
    p = Batch(dbtoolkit.amcatDB(), 5271)
    print p.id, p.name, p.project
