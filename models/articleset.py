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
from amcat.tools.djangotoolkit import get_or_create

from amcat.models.article import Article

from django.db import models

def get_or_create_articleset(name, project):
    """
    Finds an articleset based on its name. If it does not exists, it creates
    one and returns that one instead.

    @type name: unicode
    @param name: name attribute of ArticleSet
    @type project: project.Project
    @param project: project attribute of ArticleSet
    @return: ArticleSet object or None if name is None
    """
    return get_or_create(ArticleSet, name=name, project=project) if name else None

def _articles_to_ids(articles):
    """
    Convert given articles to article ids.

    @param articles: articles to convert
    @type articles: iterable with each type(object) in (int, Article)
    """
    for art in articles:
        yield art if type(art) is int else art.id

class ArticleSet(AmcatModel):
    """
    Model for the sets table. A set is part of a project and contains articles.
    It can also be seen as a 'tag' for articles.
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='articleset_id')

    name = models.CharField(max_length=200)
    project = models.ForeignKey("amcat.Project", related_name='articlesets')
    articles = models.ManyToManyField(Article, through="amcat.ArticleSetArticle", related_name="articlesets")

    codingjobset = models.BooleanField(default=False)
    batch = models.BooleanField(default=False)
    
    provenance = models.TextField(null=True)
    

    class Meta():
        app_label = 'amcat'
        db_table = 'articlesets'
        unique_together = ('name', 'project')
        ordering = ['name']

    def setType(self):
        """
        This function should return to which kind of object a set belongs to,
        in order to group a list of sets into subgroups"""
        #TODO: why is this here? And why is it called 'set', not 'get'?
        pass
        
    def add(self, *articles):
        ArticleSetArticle.objects.bulk_create(
            [ArticleSetArticle(articleset=self, article_id=artid)\
             for artid in _articles_to_ids(articles)]
        )
        
    def remove(self, *articles):
        ArticleSetArticle.objects.filter(articleset=self, article__in=articles).delete()
    
class ArticleSetArticle(AmcatModel):
    """
    ManyToMany table for article sets. An explicit model allows more prefeting in
    django queries and doesn't cost anything
    """
    id = models.AutoField(primary_key=True, db_column='id')
    articleset = models.ForeignKey(ArticleSet)
    article = models.ForeignKey(Article)

    class Meta():
        app_label = 'amcat'
        db_table="articlesets_articles"
    
    
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
            s.add(amcattest.create_test_article())
        self.assertEqual(i, len(s.articles.all()))

        
