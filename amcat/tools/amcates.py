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


from __future__ import unicode_literals, print_function, absolute_import
import logging
import pyes
from pyes import queryset
import re
from amcat.tools.toolkit import multidict
from amcat.models import ArticleSetArticle, Article
    
def _clean(text):
    if text: return re.sub('[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', text)
       
def _get_article_dict(a):
    return dict(id=a.id,
                headline=_clean(a.headline),
                body=_clean(a.text),
                byline=_clean(a.byline),
                section=_clean(a.section),
                projectid=a.project_id,
                mediumid=a.medium_id,
                page=a.pagenr,
                date=a.date)
 

class AmCATES(object):
    def __init__(self, host='localhost:9500', index='amcat'):
        self.host = host
        self.conn = pyes.ES(self.host)
        self.index = index

    def clear_index(self):
        """
        Completely removes and recreates the index. This is not always a good idea :-)
        """
        try:
            self.conn.indices.delete_index(self.index)
        except pyes.exceptions.IndexMissingException:
            pass
        self.conn.indices.create_index(self.index)
        
        
    def add_articles(self, article_ids):
        sets = multidict((aa.article_id, aa.articleset_id)
                         for aa in ArticleSetArticle.objects.filter(article__in=article_ids))
        for a in Article.objects.filter(pk__in=article_ids):
            d = _get_article_dict(a)
            d["sets"] = sets.get(a.id)
            self.conn.index(d, self.index, "article", a.id, bulk=True)
        self.conn.flush_bulk()
        self.conn.refresh(self.index)

        
    @property
    def Article(self):
        """
        Get the elastic search Article model
        """
        return queryset.generate_model(self.index, "article", es_url=self.host)
    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAmcatES(amcattest.PolicyTestCase):
    
    def test_article_date(self):
        from amcat.models import Article
        es = AmCATES(index='amcat___unittest')
        db_a = amcattest.create_test_article(text='een dit is een test bla', headline='bla bla', date='2010-01-01')
        db_a = Article.objects.get(id=db_a.id)
        es.add_articles([db_a])
        es_a  = es.Article.objects.get(id=db_a.id)
        self.assertEqual(es_a.date, db_a.date)


    def test_article_sets(self):
        es = AmCATES(index='amcat___unittest')
        a, b, c = [amcattest.create_test_article() for _x in range(3)]
        s1 = amcattest.create_test_set(articles=[a,b,c])
        s2 = amcattest.create_test_set(articles=[b,c])
        s3 = amcattest.create_test_set(articles=[b])
        es.add_articles([a,b,c])
        
        self.assertEqual(set(es.Article.objects.get(id=c.id).sets), {s1.id, s2.id})

        print(es.Article.objects.filter(sets=s2.id))
        
        
