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

from amcat.tools.model import AmcatModel

from amcat.model.project import Project
from amcat.model.article import Article
from amcat.model.user import User

from django.db import models

class Set(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='set_id')

    name = models.CharField(max_length=100, unique=True)
    project = models.ForeignKey(Project)
    articles = models.ManyToManyField(Article, db_table="sets_articles")

    class Meta():
        app_label = 'amcat'
        db_table = 'sets'

    def __unicode__(self):
        return self.name
        
    def setType(self):
        """this function should return to which kind of object a set belongs to, in order to group a list of sets into subgroups"""
        pass
        
