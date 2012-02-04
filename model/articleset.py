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
Model module for Article Sets. A Set is a generic collection of articles,
either created manually or as a result of importing articles or assigning
coding jobs.
"""

from amcat.tools.model import AmcatModel

from amcat.model.project import Project
from amcat.model.article import Article

from django.db import models

class ArticleSet(AmcatModel):
    """
    Model for the sets table. A set is part of a project and contains articles.
    It can also be seen as a 'tag' for articles.
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='articleset_id')

    name = models.CharField(max_length=100)
    project = models.ForeignKey(Project)
    articles = models.ManyToManyField(Article, db_table="articlesets_articles")

    codingjobset = models.BooleanField(default=False)
    batch = models.BooleanField(default=False)
    
    provenance = models.TextField(null=True)
    

    class Meta():
        app_label = 'amcat'
        db_table = 'articlesets'
        unique_together = ('name', 'project')

    def setType(self):
        """
        This function should return to which kind of object a set belongs to,
        in order to group a list of sets into subgroups"""
        #TODO: why is this here? And why is it called 'set', not 'get'?
        pass
        

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestArticleSet(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create a set with some articles and retrieve the articles?"""       
        s = amcattest.create_test_set()
        i = 7
        for _x in range(i):
            s.articles.add(amcattest.create_test_article())
        self.assertEqual(i, len(s.articles.all()))

        
