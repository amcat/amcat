from __future__ import unicode_literals, print_function, absolute_import
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

from amcat.tools.cachable.cachable import Cachable, DBProperty, DBProperties, ForeignKey
from amcat.model import user, permissions, article, codingjob
from amcat.tools import toolkit
from functools import partial


class Project(Cachable):
    __table__ = 'projects'
    __idcolumn__ = 'projectid'
    __labelprop__ = 'name'

    name, projectid, insertDate, description = DBProperties(4)
    articles = ForeignKey(lambda: article.Article)
    sets = ForeignKey(lambda : Set)
    insertdate = DBProperty()
    insertUser = DBProperty(lambda : user.User, getcolumn="insertuserid")
    users = ForeignKey(lambda : user.User, table="permissions_projects_users")
    codingjobs = ForeignKey(lambda : codingjob.CodingJob)
    
class Set(Cachable):
    __table__ = 'sets'
    __idcolumn__ = 'setid'
    __labelprop__ = 'name'
    
    name = DBProperty()
    project = DBProperty(lambda : Project)
    articles = ForeignKey(lambda : article.Article, table="storedresults_articles")
    
    def addArticles(self, articles):
        self.db.insertmany("storedresults_articles", ["storedresultid", "articleid"],
                           [(self.id, getAid(a)) for a in articles])
        self.removeCached("articles")
    

        
if __name__ == '__main__':
    import dbtoolkit
    p = Project(dbtoolkit.amcatDB(), 1)
    print(p.getType("name"))
    print(Project.name.getType())
