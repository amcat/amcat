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
import collections
from datetime import datetime

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

class ArticleResult(object):
    """Simple class to hold arbitrary values""" 
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))
    
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
                doc['sets'] = list(sets.get(a.id, []))
                self.es.index(index=self.index, doc_type=ARTICLE_DOCTYPE, id=a.id, body=doc)
        self.flush()

    def get_article(self, article_id):
        """
        Get a single article from the index
        """
        result = self.es.get(index=self.index, id=article_id, doc_type=ARTICLE_DOCTYPE)
        return result['_source']
        

    
    def query_ids(self, query=None, filter=None, filters={}, **kwargs):
        """
        Query the index returning a sequence of article ids for the mathced articles
        @param query: a elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
        @param filter: field filter DSL query dict
        @param filters: if filter is None, build filter from filters as accepted by build_query, e.g. sets=12345
        Note that query and filters can be combined in a single call
        """
        body = dict(build_body(query, filter, filters))

        options = dict(scroll="1m", size=1000, fields="")
        options.update(kwargs)
        res = self.es.search(index=self.index, search_type='scan', body=body, **options)
        sid = res['_scroll_id']
        while True:
            res = self.es.scroll(scroll_id=sid, scroll="1m")
            if not res['hits']['hits']:
                break
            for row in res['hits']['hits']:
                yield int(row['_id'])
            sid = res['_scroll_id']

    def query(self, query=None, filter=None, filters={}, **kwargs):
        """
        Execute a query for the given fields with the given query and filter
        @param query: a elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
        @param filter: field filter DSL query dict, defaults to _build_filter(**filters)
        @param kwargs: additional keyword arguments to pass to es.search, eg fields, sort, offset, etc
        @return: a list of named tuples containing id, score, and the requested fields
        """
        body = dict(build_body(query, filter, filters))
        if 'sort' in kwargs: body['track_scores'] = True

        log.info("es.search(body={body}, **{kwargs})".format(**locals()))
        result = self.es.search(index=self.index, body=body, **kwargs)
        for row in result['hits']['hits']:
            print(row)
            print(row['_id'], row['_score'])
            result =  ArticleResult(id=int(row['_id']), score=int(row['_score']), **row.get('fields', {}))
            if hasattr(result, 'date'): result.date = datetime.strptime(result.date, '%Y-%m-%dT%H:%M:%S')
            yield result
            
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
        solr_ids = set(self.query_ids(filters=dict(sets=aset.id)))
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

    def check_index(self):
        """
        Check whether the server is up and the index exists.
        If the server is down, raise an exception.
        If the index does not exist, try to create it.
        """
        if not self.es.ping():
            raise Exception("Elastic server cannot be reached")
        if not indices.IndicesClient(self.es).exists(self.index):
            log.info("Index {self.index} does not exist, creating".format(**locals()))
            indices.IndicesClient(self.es).create(self.index)


def build_filter(start_date=None, end_date=None, mediumid=None, ids=None, sets=None):
    """
    Build a elastic DSL query from the 'form' fields
    """

    filters = []
    if sets: filters.append(dict(terms={'sets' : _list(sets)}))
    if mediumid: filters.append(dict(terms={'mediumid' : _list(mediumid)}))

    date_range = {}
    if start_date: date_range['gte'] = start_date
    if end_date: date_range['lt'] = end_date
    if date_range: filters.append(dict(range={'date' : date_range}))

    if len(filters) == 0:
        return None
    elif len(filters) == 1:
        return filters[0]
    else:
        return {'and' : filters}

def build_body(query=None, filter=None, filters=None):
    """
    Construct the query body from the query and/or filter(s)
    (call with dict(build_body)
    @param query: a elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
    @param filter: field filter DSL query dict, defaults to _build_filter(**filters)
    """
    if filter is None: filter = build_filter(**filters)
    if filter: yield ('filter', filter)
    if query: yield ('query', {'query_string' : {'query' : query}})
        
            

        

def _list(x):
    if isinstance(x, int): return [x]
    return x
        
if __name__ == '__main__':
    ES().check_index()

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
        

    def test_date_filter(self):
        a = amcattest.create_test_article(text="artikel een", date="2001-01-01")
        b = amcattest.create_test_article(text="artikel twee", date="2002-01-01")
        c = amcattest.create_test_article(text="artikel drie", date="2003-01-01")
        
        s1 = amcattest.create_test_set(articles=[a,b,c])
        s2 = amcattest.create_test_set(articles=[a,b])
        ES().add_articles([a.id,b.id,c.id])

        self.assertEqual(set(ES().query_ids(filters=dict(start_date='2001-06-01'))), {b.id, c.id})
        # start is inclusive
        self.assertEqual(set(ES().query_ids(filters=dict(start_date='2002-01-01', end_date="2002-06-01"))),
                         {b.id})
        # end is exclusive
        self.assertEqual(set(ES().query_ids(filters=dict(start_date='2001-01-01', end_date="2003-01-01"))),
                         {a.id, b.id})

        # combining filters works
        self.assertEqual(set(ES().query_ids(filters=dict(start_date='2001-06-01', sets=s2.id))), {b.id})
        
        
        
    def test_index(self):
        import datetime
        aid = amcattest.create_test_article(text='test', headline='test_headline', date='2010-01-01').id
        db_a = Article.objects.get(id=aid)
        ES().add_articles([aid])
        a = ES().get_article(aid)
        self.assertEqual(a['body'], db_a.text)
        self.assertEqual(datetime.datetime.strptime(a['date'], "%Y-%m-%dT%H:%M:%S"), db_a.date)

    def test_query(self):
        a = amcattest.create_test_article(headline="bla", text="artikel artikel een", date="2001-01-01")
        ES().add_articles([a.id])

        
        es_a, = ES().query("een", fields=["date", "headline"])
        self.assertEqual(es_a.score, 1)
        self.assertEqual(es_a.headline, "bla")
        self.assertEqual(es_a.id, a.id)

        es_a, = ES().query("artikel")
        self.assertEqual(es_a.score, 2)

        # are scores retrieved when sorting?
        es_a, = ES().query("artikel", sort="id")
        self.assertEqual(es_a.score, 2)

        
    def test_query_ids(self):
        """Test that filters and query strings work"""
        ES().delete_index()
        m1, m2 = [amcattest.create_test_medium() for _ in range(2)]
        a = amcattest.create_test_article(text='aap noot mies', medium=m1)
        b = amcattest.create_test_article(text='noot mies wim zus', medium=m2)
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', medium=m2)

        ES().add_articles([a.id, b.id, c.id])

        self.assertEqual(set(ES().query_ids(filters=dict(mediumid=m2.id))), {b.id, c.id})
        self.assertEqual(set(ES().query_ids("no*")), {a.id, b.id})
        self.assertEqual(set(ES().query_ids("no*", filters=dict(mediumid=m2.id))), {b.id})
        self.assertEqual(set(ES().query_ids("zus AND jet", filters=dict(mediumid=m2.id))), {c.id})
        self.assertEqual(set(ES().query_ids("zus OR jet", filters=dict(mediumid=m2.id))), {b.id, c.id})
        self.assertEqual(set(ES().query_ids('"mies wim"', filters=dict(mediumid=m2.id))), {b.id})
        self.assertEqual(set(ES().query_ids('"mies wim"~5', filters=dict(mediumid=m2.id))), {b.id, c.id})
        self.assertEqual(set(ES().query_ids('"mi* wi*"~5', filters=dict(mediumid=m2.id))), {b.id, c.id})

        
    def test_articlesets(self):
        a, b, c = [amcattest.create_test_article() for _x in range(3)]
        s1 = amcattest.create_test_set(articles=[a,b,c])
        s2 = amcattest.create_test_set(articles=[b,c])
        s3 = amcattest.create_test_set(articles=[b])
        ES().add_articles([a.id,b.id,c.id])

        es_c = ES().get_article(c.id)
        self.assertEqual(set(es_c['sets']), {s1.id, s2.id})

        ids = ES().query_ids(filters=dict(sets=s1.id))
        self.assertEqual(set(ids), {a.id, b.id, c.id})

    def test_refresh_index(self):
        """Are added/removed articles added/removed from the index?"""

        s = amcattest.create_test_set(indexed=True)
        a = amcattest.create_test_article()
            
        s.add(a)
        self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s.id))))
        s.refresh_index()
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s.id))))

        s.remove(a)
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s.id))))
        s.refresh_index()
        self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s.id))))

        # test that if not set.indexed, it is not added to solr
        s = amcattest.create_test_set(indexed=False)
        s.add(a)
        s.refresh_index()
        self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s.id))))

        # test that remove from index works for larger sets
        s = amcattest.create_test_set(indexed=True)
        arts = [amcattest.create_test_article(medium=a.medium) for i in range(20)]
        s.add(*arts)

        s.refresh_index()
        solr_ids = set(ES().query_ids(filters=dict(sets=s.id)))
        self.assertEqual(set(solr_ids), {a.id for a in arts})

        s.remove(arts[0])
        s.remove(arts[-1])
        s.refresh_index()
        solr_ids = set(ES().query_ids(filters=dict(sets=s.id)))
        self.assertEqual(set(solr_ids), {a.id for a in arts[1:-1]})

        # test that changing an article's properties can be reindexed
        arts[1].medium = amcattest.create_test_medium()
        arts[1].save()

    def test_full_refresh(self):
        "test full refresh, e.g. document content change. DOES NOT WORK YET"
        query = "sets:{s.id} AND mediumid:{m}".format(m=arts[1].medium.id, **locals())
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=arts[1].medium.id))),
                         set()) # before refresh
        s.refresh_index()
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=arts[1].medium.id))),
                         {arts[1].id}) # after refresh
