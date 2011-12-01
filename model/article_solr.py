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

from amcat.tools.model import AmcatModel

from amcat.model.article import Article

from django.db import models

import logging; log = logging.getLogger(__name__)


class SolrArticle(AmcatModel):
    """
    An article on the Solr Queue needs to be updated
    """
    
    id = models.AutoField(primary_key=True, db_column="solr_article_id")
    article = models.ForeignKey(Article, db_index=True)
    started = models.BooleanField(default=False)


    class Meta():
        db_table = 'solr_articles'
        app_label = 'amcat'


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
