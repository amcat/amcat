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
Model module for the Preprocessing queue

Articles on the preprocessing queue need to be checked to see if preprocessing
needs to be done.

See http://code.google.com/p/amcat/wiki/Preprocessing
"""

from __future__ import unicode_literals, print_function, absolute_import

from django.db import models

from amcat.tools.model import AmcatModel
from amcat.tools import dbtoolkit
from amcat.tools.djangotoolkit import receiver
from amcat.models.article import Article
from amcat.models.articleset import ArticleSetArticle, ArticleSet
from amcat.models.analysis import Analysis
from amcat.models.project import Project

from django.db.models.signals import post_save, post_delete

import logging; log = logging.getLogger(__name__)

class ArticlePreprocessing(AmcatModel):
    """
    An article on the Preprocessing Queue needs to be checked for preprocessing
    """
    
    id = models.AutoField(primary_key=True)
    article_id = models.IntegerField()

    class Meta():
        db_table = 'articles_preprocessing_queue'
        app_label = 'amcat'
     
class ArticleAnalysis(AmcatModel):
    """
    The Article Analysis table keeps track of which articles are / need to be preprocessed
    """

    id = models.AutoField(primary_key=True, db_column="article_analysis_id")
    
    article = models.ForeignKey(Article)
    analysis = models.ForeignKey(Analysis)
    started = models.BooleanField(default=False)
    done = models.BooleanField(default=False)
    delete = models.BooleanField(default=False)
    
    class Meta():
        db_table = 'articles_analyses'
        app_label = 'amcat'
        unique_together = ('article', 'analysis')

class ProjectAnalysis(AmcatModel):
    """
    Explicit many-to-many projects - analyses. Hopefully this can be removed
    when prefetch_related hits the main branch.
    """
    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project)
    analysis = models.ForeignKey(Analysis)

    class Meta():
        app_label = 'amcat'
        db_table = "projects_analyses"


# Signal handlers to make sure the article preprocessing queue is filled
def _add_to_queue(aid):
    ArticlePreprocessing.objects.create(article_id = aid)

@receiver([post_save, post_delete], Article)
def handle_article(sender, instance, **kargs):
    _add_to_queue(instance.id)

@receiver([post_save, post_delete], ArticleSetArticle)
def handle_articlesetarticle(sender, instance, **kargs):
    _add_to_queue(instance.article_id)
        
@receiver([post_save], Project)
def handle_project(sender, instance, **kargs):
    for aid in instance.get_all_articles():
        _add_to_queue(aid)
        
@receiver([post_save, post_delete], ProjectAnalysis)
def handle_projectanalysis(sender, instance, **kargs):
    for aid in instance.project.get_all_articles():
        _add_to_queue(aid)

@receiver([post_save], ArticleSet)
def handle_articleset(sender, instance, **kargs):
    for a in instance.articles.all().only("id"):
        _add_to_queue(a.id)
        
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestArticlePreprocessing(amcattest.PolicyTestCase):
    
    def test_article_trigger(self):
        """Is a created or update article in the queue?"""
        self._flush_queue()
        a = amcattest.create_test_article()
        self.assertIn(a.id,  self._all_articles())
        
        self._flush_queue()
        self.assertNotIn(a.id,  self._all_articles())
        a.headline = "bla bla"
        a.save()
        self.assertIn(a.id,  self._all_articles())
        
        
    def test_articleset_triggers(self):
        """Is a article added/removed from a set in the queue?"""
        
        a = amcattest.create_test_article()
        aset = amcattest.create_test_set() 
        self._flush_queue()
        self.assertNotIn(a.id,  self._all_articles())

        aset.add(a)
        self.assertIn(a.id,  self._all_articles())
        
        self._flush_queue()
        aset.remove(a)
        self.assertIn(a.id, self._all_articles())
        
        self._flush_queue()
        aid = a.id
        a.delete()
        self.assertIn(aid, self._all_articles())

        
        b = amcattest.create_test_article()
        aset.add(b)
        self._flush_queue()
        aset.project = amcattest.create_test_project()
        aset.save()
        self.assertIn(b.id, self._all_articles())
        
        
        

    def test_project_triggers(self):
        """Check trigger on project (de)activation and analyses being added/removed from project?"""
        
        a,b = [amcattest.create_test_article() for _i in range(2)]
        s = amcattest.create_test_set(project=a.project)
        self.assertNotEqual(a.project, b.project)
        s.add(b)
        
        self._flush_queue()
        a.project.active=True
        a.project.save()
        self.assertIn(a.id, self._all_articles())
        self.assertIn(b.id, self._all_articles())

        self._flush_queue()
        n = amcattest.create_test_analysis()
        ProjectAnalysis.objects.create(project=a.project, analysis=n)
        self.assertIn(a.id, self._all_articles())
        self.assertIn(b.id, self._all_articles())
        
        
        
        
    @classmethod
    def _flush_queue(cls):
        """Flush the articles queue"""
        for sa in list(ArticlePreprocessing.objects.all()): sa.delete()

    @classmethod
    def _all_articles(cls):
        """List all articles on the queue"""
        return {sa.article_id for sa in ArticlePreprocessing.objects.all()}
        
if __name__ == '__main__':

    t = TestArticlePreprocessing()
    t._flush_queue()

    a = amcattest.create_test_article()
    print(a.id, t._all_articles())
