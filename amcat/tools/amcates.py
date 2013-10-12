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
from elasticsearch.client import indices, cluster
from elasticsearch.serializer import JSONSerializer
from django.conf import settings

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
HIGHLIGHT_OPTIONS = {'fields' : {'body' : {"fragment_size" : 100, "number_of_fragments" : 3},
                                 'headline' : {}}}
LEAD_SCRIPT_FIELD = {"lead" : {'lang' : 'python',
                               "script" : '_source["body"] and _source["body"][:300] + "..."'}}


class Result(object):
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
            self.create_index()
        x = cluster.ClusterClient(self.es).health(self.index, wait_for_status='yellow')

    def add_articles(self, article_ids, flush=True):
        """
        Add the given article_ids to the index
        """
        sets = multidict((aa.article_id, aa.articleset_id)
                         for aa in ArticleSetArticle.objects.filter(article__in=article_ids))
        bodies = []
        for a in Article.objects.filter(pk__in=article_ids):
            doc = _get_article_dict(a)
            doc['sets'] = list(sets.get(a.id, []))
            bodies.append(doc)
        self.bulk_index(bodies)
        if flush:
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

    def query(self, query=None, filter=None, filters={}, highlight=False, lead=False, **kwargs):
        """
        Execute a query for the given fields with the given query and filter
        @param query: a elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
        @param filter: field filter DSL query dict, defaults to _build_filter(**filters)
        @param kwargs: additional keyword arguments to pass to es.search, eg fields, sort, offset, etc
        @return: a list of named tuples containing id, score, and the requested fields
        """
        body = dict(build_body(query, filter, filters))
        if 'sort' in kwargs: body['track_scores'] = True
        if highlight: body['highlight'] = HIGHLIGHT_OPTIONS
        if lead: body['script_fields'] = LEAD_SCRIPT_FIELD 

        log.info("es.search(body={body}, **{kwargs})".format(**locals()))
        result = self.es.search(index=self.index, body=body, **kwargs)
        for row in result['hits']['hits']:
            result =  Result(id=int(row['_id']), score=int(row['_score']), **row.get('fields', {}))
            if 'highlight' in row: result.highlight = row['highlight']
            if hasattr(result, 'date'): result.date = datetime.strptime(result.date, '%Y-%m-%dT%H:%M:%S')
            yield result
            
    def remove_from_set(self, setid, aids):
        """Remove the given articles from the given set"""
        if not aids: return
        script = 'ctx._source.sets = ($ in ctx._source.sets if $ != set)'
        self.bulk_update(aids, script, params={'set' : setid})
        self.flush()

    def add_to_set(self, setid, aids):
        """Add the given articles to the given set"""
        if not aids: return
        script = 'if (!(ctx._source.sets contains set)) {ctx._source.sets += set}'
        self.bulk_update(aids, script, params={'set' : setid})

    def bulk_index(self, bodies):
        serialize = JSONSerializer().dumps
        bulk = []
        for body in bodies:
            bulk.append(serialize(dict(index={'_id' : body['id']})))
            bulk.append(serialize(body))
        r = self.es.bulk(body=bulk, index=self.index, doc_type=ARTICLE_DOCTYPE)
        
    def bulk_update(self, aids, script, params):
        payload = json.dumps(dict(script=script, params=params))
        for batch in splitlist(aids, itemsperbatch=100):
            bulk = []
            for aid in batch:
                bulk.append(json.dumps(dict(update={'_id': aid})))
                bulk.append(payload)
            bulk = "\n".join(bulk) + "\n"
            r = self.es.bulk(body=bulk, index=self.index, doc_type=ARTICLE_DOCTYPE)
        
    def refresh_articleset_index(self, aset, full_refresh=False):
        """
        Make sure the given article set is correctly stored in the index
        """
        self.check_index() # make sure index exists and is at least 'yellow'
        
        log.debug("Getting SOLR ids from set")
        solr_set_ids = set(self.query_ids(filters=dict(sets=aset.id)))
        log.debug("Getting DB ids")
        db_ids = aset._get_article_ids()
        log.debug("Getting SOLR ids")
        solr_ids = set(self.in_index(db_ids))

        to_remove = solr_set_ids - db_ids
        if full_refresh:
            to_add_docs = db_ids
            to_add_set = set()
        else:
            to_add_docs = db_ids - solr_ids
            to_add_set = (db_ids & solr_ids) - solr_set_ids

        log.warn("Refreshing index, full_refresh={full_refresh},"
                 "|solr_set_ids|={nsolrset}, |db_set_ids|={ndb}, |solr_ids|={nsolr} "
                 "|to_add| = {nta}, |to_add_set|={ntas}, |to_remove_set|={ntr}"
                 .format(nsolr=len(solr_ids), nsolrset=len(solr_set_ids), ndb=len(db_ids),
                         nta=len(to_add_docs), ntas=len(to_add_set), ntr=len(to_remove),**locals()))

        for i, batch in enumerate(splitlist(to_remove, itemsperbatch=1000)):
            self.remove_from_set(aset.id, batch)
            log.debug("Removed batch {i}".format(**locals()))
        for i, batch in enumerate(splitlist(to_add_set, itemsperbatch=1000)):
            self.add_to_set(aset.id, batch)
            log.debug("Added batch {i} to set".format(**locals()))
        for i, batch in enumerate(splitlist(to_add_docs, itemsperbatch=100)):
            self.add_articles(batch, flush=False)
            log.debug("Added batch {i} to index".format(**locals()))

        self.flush()


    def aggregate_query(self, query=None, filters=None, group_by=None, date_interval='month'):
        """
        Compute an aggregate query, e.g. select count(*) where <filters> group by <group_by>
        If date is used as a group_by variable, uses date_interval to bin it
        Currently, group by must be a single field as elastic doesn't support multiple group by
        """
        filter = build_filter(**filters)
        body = dict(build_body(query))
        body['facets'] = {}
        if group_by == 'date':
            body['facets']['group'] = {'date_histogram' : {'field' : group_by, 'interval' : date_interval}}
        else:
            body['facets']['group'] = {'terms' : {'field' : group_by}}
        body['facets']['group']['facet_filter'] = filter
        result = self.es.search(index=self.index, body=body, size=0)
        if group_by == 'date':
            for row in result['facets']['group']['entries']:
                yield get_date(row['time']), row['count']

        else:
            for row in result['facets']['group']['terms']:
                yield row['term'], row['count']


    def statistics(self, query=None, filters=None):
        """
        Compute and return a Result object with n, start_date and end_date for the selection
        """
        filter = build_filter(**filters)
        body = dict(build_body(query))
        body['facets'] = {'stats' : {'statistical' : {'field' : 'date'}}}
        body['facets']['stats']['facet_filter'] = filter        
        stats = self.es.search(index=self.index, body=body, size=0)['facets']['stats']
        result = Result()
        result.n = stats['count']
        result.start_date=get_date(stats['min'])
        result.end_date=get_date(stats['max'])
        return result

    def list_media(self, query=None, filters=None):
        """
        List a sequence of medium_ids that exist in the selection
        """
        for medium_id, count in self.aggregate_query(query, filters, group_by="mediumid"):
            yield medium_id

    def in_index(self, ids):
        """
        Check whether the given ids are already indexed.
        @return: a sequence of ids that are in the index
        """
        if not isinstance(ids, list): ids = list(ids)
        log.info("Checking existence of {nids} documents".format(nids=len(ids)))
        if not ids: return
        for batch in splitlist(ids, itemsperbatch=10000):
            result = self.es.mget(index=self.index, doc_type=ARTICLE_DOCTYPE, body={"ids": batch}, fields=[])
            for doc in result['docs']:
                if doc['exists']: yield int(doc['_id'])

        
            
def get_date(timestamp):
    d = datetime.fromtimestamp(timestamp/1000)
    return datetime(d.year, d.month, d.day)

def build_filter(start_date=None, end_date=None, mediumid=None, ids=None, sets=None):
    """
    Build a elastic DSL query from the 'form' fields
    """

    _list = lambda x: ([x] if isinstance(x, int) else x)

    filters = []
    if sets: filters.append(dict(terms={'sets' : _list(sets)}))
    if mediumid: filters.append(dict(terms={'mediumid' : _list(mediumid)}))

    date_range = {}
    if start_date: date_range['gte'] = start_date
    if end_date: date_range['lt'] = end_date
    if date_range: filters.append(dict(range={'date' : date_range}))

    if ids: filters.append(dict(ids={'values' : _list(ids)}))
    
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
    if filter is None and filters: filter = build_filter(**filters)
    if filter: yield ('filter', filter)
    if query: yield ('query', {'query_string' : {'query' : query}})


    
        
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
        

    def test_aggregate(self):
        m1, m2, m3 = [amcattest.create_test_medium() for _ in range(3)]
        unused = amcattest.create_test_article(text='aap noot mies', medium=m3)
        a = amcattest.create_test_article(text='aap noot mies', medium=m1, date='2001-01-01')
        b = amcattest.create_test_article(text='noot mies wim zus', medium=m2, date='2001-02-01')
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', medium=m2, date='2002-01-01')
        d = amcattest.create_test_article(text='noot mies wim zus', medium=m2, date='2001-02-03')
        s1 = amcattest.create_test_set(articles=[a,b,c, d])
        s2 = amcattest.create_test_set(articles=[unused])
        ES().add_articles([unused.id, a.id,b.id,c.id, d.id])

        # counts per medium
        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="mediumid")),
                         {m1.id : 1, m2.id : 3})
        
        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="date", date_interval="year")),
                         {datetime(2001,1,1) : 3, datetime(2002,1,1) : 1})
        
        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="date", date_interval="month")),
                         {datetime(2001,1,1) : 1, datetime(2002,1,1) : 1, datetime(2001,2,1) : 2})
        
        # set statistics
        stats = ES().statistics(filters=dict(sets=s1.id))
        self.assertEqual(stats.n, 4)
        self.assertEqual(stats.start_date, datetime(2001,1,1))
        self.assertEqual(stats.end_date, datetime(2002,1,1))

        # media list
        self.assertEqual(set(ES().list_media(filters=dict(sets=s1.id))),
                         {m1.id, m2.id})
        
        
    def test_date_filter(self):
        a = amcattest.create_test_article(text="artikel een", date="2001-01-01")
        b = amcattest.create_test_article(text="artikel twee", date="2002-01-01")
        c = amcattest.create_test_article(text="artikel drie", date="2003-01-01")
        
        s1 = amcattest.create_test_set(articles=[a,b,c])
        s2 = amcattest.create_test_set(articles=[a,b])
        ES().add_articles([a.id,b.id,c.id])

        self.assertEqual(set(ES().query_ids(filters=dict(sets=s1.id, start_date='2001-06-01'))), {b.id, c.id})
        # start is inclusive
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s1.id, start_date='2002-01-01', end_date="2002-06-01"))),
                         {b.id})
        # end is exclusive
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s1.id, start_date='2001-01-01', end_date="2003-01-01"))),
                         {a.id, b.id})

        # combining filters works
        self.assertEqual(set(ES().query_ids(filters=dict(start_date='2001-06-01', sets=s2.id))), {b.id})
        
        
        
    def test_index(self):
        import datetime
        aid = amcattest.create_test_article(text='test\n\n\tweede alinea', headline='test headline;\nmet enter', date='2010-01-01').id
        db_a = Article.objects.get(id=aid)
        ES().add_articles([aid])
        a = ES().get_article(aid)
        self.assertEqual(a['body'], db_a.text)
        self.assertEqual(a['headline'], db_a.headline)
        self.assertEqual(datetime.datetime.strptime(a['date'], "%Y-%m-%dT%H:%M:%S"), db_a.date)

    def test_query(self):
        ES().delete_index()
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

    def test_complex_phrase_query(self):
        """Test complex phrase queries. DOES NOT WORK YET"""
        a = amcattest.create_test_article(text='aap noot mies')
        b = amcattest.create_test_article(text='noot mies wim zus')
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet')
        s1 = amcattest.create_test_set(articles=[a,b,c])
        ES().add_articles([a.id, b.id, c.id])
        self.assertEqual(set(ES().query_ids('"mi* wi*"~5', filters=dict(sets=s1.id))), {b.id, c.id})

        
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

        # check adding of existing articles to a new set:
        s2 = amcattest.create_test_set()
        s2.add(a)
        s2.refresh_index()
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s2.id))))
        # check that removing of articles from a set works and does not affect
        # other sets
        s2.remove(a)        
        s2.refresh_index()
        self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s2.id))))
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s.id))))
        
        
        
        s.remove(a)
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s.id))))
        s.refresh_index()
        self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s.id))))

        # test that if not set.indexed, it is not added to solr
        # Remove test since .indexed is deprecated
        #s = amcattest.create_test_set(indexed=False)
        #s.add(a)
        #s.refresh_index()
        #self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s.id))))

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
        "test full refresh, e.g. document content change"
        m1, m2 = [amcattest.create_test_medium() for _ in range(2)]
        a = amcattest.create_test_article(text='aap noot mies', medium=m1)
        s = amcattest.create_test_set()
        s.add(a)
        s.refresh_index()
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=m1.id))), {a.id})

        a.medium = m2
        a.save()
        s.refresh_index(full_refresh=False) # a should NOT be reindexed
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=m1.id))), {a.id})
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=m2.id))), set())

        s.refresh_index(full_refresh=True)
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=m1.id))), set())
        self.assertEqual(set(ES().query_ids(filters=dict(sets=s.id, mediumid=m2.id))), {a.id})
