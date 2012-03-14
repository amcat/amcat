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
from amcat.models.article import Article
from amcat.models.analysis import Analysis
from amcat.models.project import Project

import logging; log = logging.getLogger(__name__)

class ArticlePreprocessing(AmcatModel):
    """
    An article on the Preprocessing Queue needs to be checked for preprocessing
    """
    
    id = models.AutoField(primary_key=True, db_column="solr_article_id")
    article_id = models.IntegerField()

    class Meta():
        db_table = 'articles_preprocessing_queue'
        app_label = 'amcat'

        
def create_triggers():
    """Create the triggers for update/insert articles

    Assumes postgres DB with plpgsql language active
    """
    db = dbtoolkit.PostgreSQL()

    sql = """BEGIN
                IF (TG_OP = 'DELETE') THEN
                  INSERT INTO articles_preprocessing_queue (article_id) SELECT OLD.article_id;
                  RETURN OLD;
                ELSE
                  INSERT INTO articles_preprocessing_queue (article_id) SELECT NEW.article_id;
                  RETURN NEW;
                END IF;
             END;"""
    db.create_trigger("articles", "preprocessing_queue_articles", sql, actions=("INSERT","UPDATE", "DELETE"))
    db.create_trigger("articlesets_articles", "preprocessing_queue_articlesets", sql,
                      actions=("INSERT","DELETE"))

class ArticleAnalysis(AmcatModel):
    """
    The Article Analysis table keeps track of which articles are / need to be preprocessed
    """

    id = models.AutoField(primary_key=True, db_column="article_analysis_id")
    
    article_id = models.ForeignKey(Article)
    analysis_id = models.ForeignKey(Analysis)
    started = models.BooleanField(default=False)
    done = models.BooleanField(default=False)
    delete = models.BooleanField(default=False)
    
    class Meta():
        db_table = 'articles_analyses'
        app_label = 'amcat'

class ProjectAnalysis(AmcatModel):
    """
    Explicit many-to-many projects - analyses. Hopefully this can be removed
    when prefetch_related hits the main branch.
    """
    id = models.AutoField(primary_key=True, db_column='articleset_article_id')
    project = models.ForeignKey(Project)
    analysis = models.ForeignKey(Analysis)

    class Meta():
        app_label = 'amcat'
        db_table = "projects_analyses"
    
        
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestArticlePreprocessing(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we add an article to the queue"""
        a = amcattest.create_test_article()
        q = ArticlePreprocessing.objects.create(article=a)

        
    def test_article_trigger(self):
        """Is a created or update article in the queue?"""
        if not dbtoolkit.is_postgres(): return # no triggers in sqlite
        
        self._flush_queue()
        a = amcattest.create_test_article()
        self.assertIn(a.id,  self._all_articles())
        
        self._flush_queue()
        self.assertNotIn(a.id,  self._all_articles())
        a.headline = "bla bla"
        a.save()
        self.assertIn(a.id,  self._all_articles())
        
        
    def test_articleset_trigger(self):
        """Is a article added/removed from a set in the queue?"""
        if not dbtoolkit.is_postgres(): return # no triggers in sqlite
        
        a = amcattest.create_test_article()
        aset = amcattest.create_test_set() 
        self._flush_queue()
        self.assertNotIn(a.id,  self._all_articles())

        aset.articles.add(a)
        self.assertIn(a.id,  self._all_articles())
        
        self._flush_queue()
        self.assertNotIn(a.id, self._all_articles())
        aset.articles.remove(a)
        self.assertIn(a.id, self._all_articles())
        
        self._flush_queue()
        self.assertNotIn(a.id, self._all_articles())
        aid = a.id
        a.delete()
        self.assertIn(aid, self._all_articles())

    @classmethod
    def _flush_queue(cls):
        """Flush the articles queue"""
        for sa in list(ArticlePreprocessing.objects.all()): sa.delete()

    @classmethod
    def _all_articles(cls):
        """List all articles on the queue"""
        return {sa.article_id for sa in ArticlePreprocessing.objects.all()}
        
if __name__ == '__main__':

    a = amcattest.create_test_article()
    print(a.id, TestArticlePreprocessing._all_articles())
    TestArticlePreprocessing._flush_queue()
    a.delete()
    print(TestArticlePreprocessing._all_articles())
    
