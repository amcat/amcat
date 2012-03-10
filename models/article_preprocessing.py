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
Model module for the SOLR queue
"""
from __future__ import unicode_literals, print_function, absolute_import

from django.db import models

from amcat.tools.model import AmcatModel
from amcat.tools import dbtoolkit
from amcat.models.article import Article

import logging; log = logging.getLogger(__name__)

class ArticlePreprocesing(AmcatModel):
    """
    An article on the Solr Queue needs to be updated
    """
    
    id = models.AutoField(primary_key=True, db_column="solr_article_id")
    article = models.ForeignKey(Article, db_index=True)
    analysis = models.ForeignKey(Analysis, db_index=True)

    class Meta():
        db_table = 'articles_preprocessing'
        app_label = 'amcat'

        
def create_triggers():
    """Create the triggers for update/insert articles

    Assumes postgres DB with plpgsql language active
    """
    db = dbtoolkit.PostgreSQL()

    sql = """BEGIN
                IF (TG_OP = 'DELETE') THEN
                  INSERT INTO solr_articles (article_id, started) SELECT OLD.article_id, true;
                  RETURN OLD;
                ELSE
                  INSERT INTO solr_articles (article_id, started) SELECT NEW.article_id, true;
                  RETURN NEW;
                END IF;
             END;"""
    db.create_trigger("articles", "solr_queue_articles", sql, actions=("INSERT","UPDATE"))
    db.create_trigger("articlesets_articles", "solr_queue_articlesets", sql,
                      actions=("INSERT","DELETE"))

        
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestSolrArticle(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we add an article to the queue"""
        a = amcattest.create_test_article()
        q = SolrArticle.objects.create(article=a)
        self.assertFalse(q.started)

    def _flush_queue(self):
        """Flush the articles queue"""
        for sa in list(SolrArticle.objects.all()): sa.delete()

    def _all_articles(self):
        """List all articles on the queue"""
        return [sa.article for sa in SolrArticle.objects.all()]
        
    def test_article_trigger(self):
        """Is a created or update article in the queue?"""
        if not dbtoolkit.is_postgres(): return # no triggers in sqlite
        
        self._flush_queue()
        a = amcattest.create_test_article()
        self.assertIn(a,  self._all_articles())
        
        self._flush_queue()
        self.assertNotIn(a,  self._all_articles())
        a.headline = "bla bla"
        a.save()
        self.assertIn(a,  self._all_articles())
        
        
    def test_articleset_trigger(self):
        """Is a article added/removed from a set in the queue?"""
        if not dbtoolkit.is_postgres(): return # no triggers in sqlite
        
        a = amcattest.create_test_article()
        aset = amcattest.create_test_set() 
        self._flush_queue()
        self.assertNotIn(a,  self._all_articles())

        aset.articles.add(a)
        self.assertIn(a,  self._all_articles())
        
        self._flush_queue()
        self.assertNotIn(a, self._all_articles())
        aset.articles.remove(a)
        self.assertIn(a, self._all_articles())
        
