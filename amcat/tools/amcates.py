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
log = logging.getLogger(__name__)
import re
import requests
import json
from amcat.tools.toolkit import multidict, splitlist
from amcat.models import ArticleSetArticle, Article
from elasticsearch import Elasticsearch
from elasticsearch.client import indices
from django.conf import settings
from elasticutils import S # used for build_query


def _clean(s):
    if s: return re.sub('[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', s)
    
def _get_article_dict(art):
    return dict(id=art.id,
                headline=_clean(art.headline),
                body=_clean(art.text),
                byline=_clean(art.byline),
                section=_clean(art.section),
                projectid=art.project_id,
                mediumid=art.medium_id,
                page=art.pagenr,
                date=art.date)

ARTICLE_DOCTYPE='article'

class ES(object):
    def __init__(self, index=None):
        self.es = Elasticsearch()
        self.index = settings.ES_INDEX if index is None else index

    def flush(self):
        indices.IndicesClient(self.es).flush()

    def delete_index(self):
        try:
            indices.IndicesClient(self.es).delete(self.index)
        except Exception, e:
            if 'IndexMissingException' in unicode(e): return
            raise            
    def create_index(self):
            indices.IndicesClient(self.es).create(self.index)
        
    
        
        
    def add_articles(self, article_ids):
        """
        Add the given article_ids to the index
        """
        for batch in splitlist(article_ids, itemsperbatch=1000):
            sets = multidict((aa.article_id, aa.articleset_id)
                             for aa in ArticleSetArticle.objects.filter(article__in=batch))
            
            for a in Article.objects.filter(pk__in=batch):
                doc = _get_article_dict(a)
                doc['sets'] = list(sets.get(a.id))
                self.es.index(index=self.index, doc_type=ARTICLE_DOCTYPE, id=a.id, body=doc)
        self.flush()

    def get_article(self, article_id):
        """
        Get a single article from the index
        """
        result = self.es.get(index=self.index, id=article_id, doc_type=ARTICLE_DOCTYPE)
        return result['_source']
        
    
    def query_ids(self, **filters):
        q = S().filter(**filters)._build_query()
        print(q)
        res = self.es.search(index=self.index, search_type='scan', body=q, fields="", scroll="1m", size=1000)
        print("Got %d Hits:" % res['hits']['total'])
        sid = res['_scroll_id']

        while True:
            res = self.es.scroll(scroll_id=sid, scroll="1m")
            if not res['hits']['hits']:
                break
            for row in res['hits']['hits']:
                yield int(row['_id'])
            sid = res['_scroll_id']

    def remove_from_set(self, setid, aids):
        """Remove the given articles from the given set"""
        script = 'ctx._source.sets = ($ in ctx._source.sets if $ != set)'
        self.bulk_update(aids, script, params={'set' : setid})
        self.flush()

    def add_to_set(self, setid, aids):
        """Add the given articles to the given set"""
        script = 'if (!(ctx._source.sets contains set)) {ctx._source.sets += set}'
        self.bulk_update(aids, script, params={'set' : setid})
    
    def bulk_update(self, aids, script, params):
        payload = json.dumps(dict(script=script, params=params))
        for batch in splitlist(aids, itemsperbatch=100):
            bulk = []
            for aid in batch:
                bulk.append(json.dumps(dict(update={'_id': aid})))
                bulk.append(payload)
            bulk = "\n".join(bulk) + "\n"
            r = self.es.bulk(body=bulk, index=self.index, doc_type=ARTICLE_DOCTYPE)
            print(">>>>", r)
            #if r.status_code != 200:
            #    raise Exception(r.text)
        
    def refresh_articleset_index(self, aset, full_refresh=False):
        """
        Make sure the given article set is correctly stored in the index
        """

        log.debug("Getting SOLR ids")
        solr_ids = set(self.query_ids(sets=aset.id))
        log.debug("Getting DB ids")
        db_ids = aset._get_article_ids() if aset.indexed else set()

        to_remove = solr_ids - db_ids
        to_add = db_ids if full_refresh else  db_ids - solr_ids

        log.warn("Refreshing index, full_refresh={full_refresh}, |solr_ids|={nsolr}, |db_ids|={ndb}, "
                 "|to_add|={nta}, |to_remove|={ntr}"
                 .format(nsolr=len(solr_ids), ndb=len(db_ids), nta=len(to_add), ntr=len(to_remove),**locals()))

        for i, batch in enumerate(splitlist(to_remove)):
            self.remove_from_set(aset.id, batch)
            log.debug("Removed batch {i}".format(**locals()))
        for i, batch in enumerate(splitlist(to_add, itemsperbatch=1000)):
            self.add_articles(batch)
            log.debug("Added batch {i}".format(**locals()))
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAmcatES(amcattest.PolicyTestCase):

    @classmethod
    def setUpClass(cls):
        cls.old_index = settings.ES_INDEX
        settings.ES_INDEX += "__unittest"
        ES().delete_index()
        ES().create_index()
        
    
    def test_index(self):
        import datetime
        aid = amcattest.create_test_article(text='test', headline='test_headline', date='2010-01-01').id
        db_a = Article.objects.get(id=aid)
        ES().add_articles([aid])
        a = ES().get_article(aid)
        self.assertEqual(a['body'], db_a.text)
        self.assertEqual(datetime.datetime.strptime(a['date'], "%Y-%m-%dT%H:%M:%S"), db_a.date)

    def test_articlesets(self):
        a, b, c = [amcattest.create_test_article() for _x in range(3)]
        s1 = amcattest.create_test_set(articles=[a,b,c])
        s2 = amcattest.create_test_set(articles=[b,c])
        s3 = amcattest.create_test_set(articles=[b])
        ES().add_articles([a.id,b.id,c.id])

        es_c = ES().get_article(c.id)
        self.assertEqual(set(es_c['sets']), {s1.id, s2.id})

        ids = ES().query_ids(sets=s1.id)
        self.assertEqual(set(ids), {a.id, b.id, c.id})

    def test_refresh_index(self):
        """Are added/removed articles added/removed from the index?"""

        s = amcattest.create_test_set(indexed=True)
        a = amcattest.create_test_article()
            
        s.add(a)
        self.assertEqual(set(), set(ES().query_ids(sets=s.id)))
        s.refresh_index()
        self.assertEqual({a.id}, set(ES().query_ids(sets=s.id)))

        s.remove(a)
        self.assertEqual({a.id}, set(ES().query_ids(sets=s.id)))
        s.refresh_index()
        self.assertEqual(set(), set(ES().query_ids(sets=s.id)))

        # test that if not set.indexed, it is not added to solr
        s = amcattest.create_test_set(indexed=False)
        s.add(a)
        s.refresh_index()
        self.assertEqual(set(), set(ES().query_ids(sets=s.id)))

        # test that remove from index works for larger sets
        s = amcattest.create_test_set(indexed=True)
        arts = [amcattest.create_test_article(medium=a.medium) for i in range(20)]
        s.add(*arts)

        s.refresh_index()
        solr_ids = set(ES().query_ids(sets=s.id))
        self.assertEqual(set(solr_ids), {a.id for a in arts})

        s.remove(arts[0])
        s.remove(arts[-1])
        s.refresh_index()
        solr_ids = set(ES().query_ids(sets=s.id))
        self.assertEqual(set(solr_ids), {a.id for a in arts[1:-1]})

        # test that changing an article's properties can be reindexed
        arts[1].medium = amcattest.create_test_medium()
        arts[1].save()

    def test_full_refresh(self):
        # DOES NOT WORK YET
        query = "sets:{s.id} AND mediumid:{m}".format(m=arts[1].medium.id, **locals())
        self.assertEqual(set(ES().query_ids(sets=s.id, mediumid=arts[1].medium.id)), set()) # before refresh
        s.refresh_index()
        self.assertEqual(set(ES().query_ids(sets=s.id, mediumid=arts[1].medium.id)), {arts[1].id}) # after refresh
