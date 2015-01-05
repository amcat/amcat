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
import collections
from datetime import datetime

from hashlib import sha224 as hash_class
from json import dumps as serialize

from amcat.tools import queryparser, toolkit
from amcat.tools.toolkit import multidict, splitlist
from elasticsearch import Elasticsearch, connection
from elasticsearch.client import indices, cluster
from django.conf import settings
from amcat.tools.caching import cached
from amcat.tools.progress import NullMonitor

def _clean(s):
    if s: return re.sub('[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', s)

def get_article_dict(art, sets=None):
    date = art.date
    if date:
        if isinstance(art.date, (str, unicode)):
            date = toolkit.readDate(date)
        date = date.isoformat()
    d = dict(
        # dublin core elements
        id = art.id,
        headline=_clean(art.headline),
        text=_clean(art.text),
        date=date,
        creator=_clean(art.author),

        # other elements
        projectid=art.project_id,
        mediumid=art.medium_id,
        medium=art.medium.name,
        byline=_clean(art.byline),
        section=_clean(art.section),
        page=art.pagenr,
        addressee=_clean(art.addressee),
        length=art.length,
        sets = sets
        )

    d['hash'] = _get_hash(d)
    return d

def _get_hash(article_dict):
    c =hash_class()
    keys = sorted(k for k in article_dict.keys()
                  if k not in ('id', 'sets', 'hash', 'medium', 'projectid'))
    for k in keys:
        v = article_dict[k]
        if isinstance(v, int):
            c.update(str(v))
        elif isinstance(v, unicode):
            c.update(v.encode('utf-8'))
        elif v is not None:
            c.update(v)
    return c.hexdigest()

HIGHLIGHT_OPTIONS = {
    'fields': {
        'text': {
            "fragment_size": 100,
            "number_of_fragments": 3
        },
        'headline': {}
    }
}

LEAD_SCRIPT_FIELD = {
    "lead": {
        'lang': 'python',
        "script": r'_source["text"].replace("\r", "").split("\n\n")[0]'
    }
}

UPDATE_SCRIPT_REMOVE_FROM_SET = 'ctx._source.sets = ($ in ctx._source.sets if $ != set)'

UPDATE_SCRIPT_ADD_TO_SET = 'if (!(ctx._source.sets contains set)) {ctx._source.sets += set}'

UPDATE_SCRIPT_ADD_TO_SET = ("if (ctx._source.sets == null) {ctx._source.sets = [set]} "
                            "else { if (!(ctx._source.sets contains set)) {ctx._source.sets += set}}")


class SearchResult(object):
    """Iterable collection of results that also has total"""
    def __init__(self, results, fields, score, body, query=None):
        "@param results: the raw results dict from elasticsearch::search"
        self._results = results
        self.hits = self._results['hits']['hits']
        self.total = self._results['hits']['total']
        self.fields = fields
        self.score = score
        self.body = body
        self.query = query

    @property
    @cached
    def results(self):
        return [Result.from_hit(self, h, self.fields, self.score) for h in self.hits]

    def __len__(self):
        return len(self.hits)

    def __iter__(self):
        return iter(self.results)

    def __getitem__(self, i):
        return self.results[i]

    def as_dicts(self):
        "Return the results as fieldname : value dicts"
        return [r.__dict__ for r in self]


class Result(object):
    """Simple class to hold arbitrary values"""
    @classmethod
    def from_hit(cls, searchresult, row, fields, score=True):
        "@param hit: elasticsearch hit dict"
        field_dict = {f: None for f in fields}
        if 'fields' in row:
            for (k, v) in row['fields'].iteritems():
                if k != "sets":
                    # elastic 1.0 always returns arrays, we only want
                    # sets in a list, the rest should be 'scalarized'
                    if isinstance(v, list):
                        v = v[0]
                field_dict[k] = v

        result =  Result(id=int(row['_id']), _searchresult=searchresult, **field_dict)
        if score: result.score = int(row['_score'])
        if 'highlight' in row: result.highlight = row['highlight']
        if hasattr(result, 'date'):
            if len(result.date) == 10:
                result.date = datetime.strptime(result.date, '%Y-%m-%d')
            else:
                result.date = datetime.strptime(result.date[:19], '%Y-%m-%dT%H:%M:%S')
        return result

    @classmethod
    def from_stats(cls, stats, date=False, **kargs):
        """Create a Result object from an ES statistics dict {u'count': 0, u'max': ...}"""
        result = Result(**kargs)
        result.count = stats['count']
        if result.count == 0:
            result.start_date, result.end_data = None, None
        else:
            f = get_date if date else int
            result.min=f(stats['min'])
            result.max=f(stats['max'])
        return result

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))

class ES(object):
    def __init__(self, index=None, doc_type=None, timeout=60, **args):
        elhost = {"host":settings.ES_HOST, "port":settings.ES_PORT}
        self.es = Elasticsearch(hosts=[elhost, ], timeout=timeout, **args)
        self.index = settings.ES_INDEX if index is None else index
        self.doc_type = settings.ES_ARTICLE_DOCTYPE if doc_type is None else doc_type

    def flush(self):
        indices.IndicesClient(self.es).flush()

    def highlight_article(self, aid, query):
        query = queryparser.parse_to_terms(query).get_dsl()

        highlight_opts = {"highlight_query" : query, "number_of_fragments": 0}
        body = dict(filter=build_filter(ids=aid),
                highlight={"fields" : {"text" : highlight_opts, "headline" : highlight_opts, "byline" : highlight_opts,}})
        r = self.search(body, fields=[])
        try:
            hl = r['hits']['hits'][0]['highlight']
            return {f : hl[f][0] for f in hl}
        except KeyError:
            log.exception("Could not get highlights from {r!r}".format(**locals()))


    def clear_cache(self):
        indices.IndicesClient(self.es).clear_cache()

    def delete_index(self):
        try:
            indices.IndicesClient(self.es).delete(self.index)
        except Exception, e:
            if 'IndexMissingException' in unicode(e): return
            raise

    def create_index(self):
        body = {
            "settings" : settings.ES_SETTINGS,
            "mappings" : {settings.ES_ARTICLE_DOCTYPE : settings.ES_MAPPING}}
        indices.IndicesClient(self.es).create(self.index, body)

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


    def get(self, id, **options):
        """
        Get a single article from the index
        """
        kargs = dict(index=self.index, doc_type=self.doc_type)
        kargs.update(options)
        return self.es.get_source(id=id, **kargs)

    def search(self, body, **options):
        """
        Perform a 'raw' search on the underlying ES index
        """
        kargs = dict(index=self.index, doc_type=self.doc_type)
        kargs.update(options)
        return self.es.search(body=body, **kargs)


    def query_ids(self, query=None, filters={}, **kwargs):
        """
        Query the index returning a sequence of article ids for the mathced articles
        @param query: a elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
        @param filter: field filter DSL query dict
        @param filters: if filter is None, build filter from filters as accepted by build_query, e.g. sets=12345
        Note that query and filters can be combined in a single call
        """
        body = dict(build_body(query, filters, query_as_filter=True))
        options = dict(scroll="1m", size=1000, fields="")
        options.update(kwargs)
        res = self.search(body, search_type='scan', **options)
        sid = res['_scroll_id']
        while True:
            res = self.es.scroll(scroll_id=sid, scroll="1m")
            if not res['hits']['hits']:
                break
            for row in res['hits']['hits']:
                yield int(row['_id'])
            sid = res['_scroll_id']

    def query(self, query=None, filters={}, highlight=False, lead=False, fields=[], score=True, **kwargs):
        """
        Execute a query for the given fields with the given query and filter
        @param query: a elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
        @param filter: field filter DSL query dict, defaults to build_filter(**filters)
        @param kwargs: additional keyword arguments to pass to es.search, eg fields, sort, from_, etc
        @return: a list of named tuples containing id, score, and the requested fields
        """
        body = dict(build_body(query, filters, query_as_filter=(not (highlight or score))))
        if (highlight and not score):
            body['query'] = {'constant_score' : {'query' : body['query']}}

        if 'sort' in kwargs: body['track_scores'] = True

        if highlight:
            if isinstance(highlight, dict):
                body['highlight'] = highlight
            else:
                body['highlight'] = HIGHLIGHT_OPTIONS
        if lead: body['script_fields'] = LEAD_SCRIPT_FIELD

        result = self.search(body, fields=fields, **kwargs)
        return SearchResult(result, fields, score, body, query=query)

    def query_all(self, *args, **kargs):
        kargs.update({"from_" : 0})
        size = kargs.setdefault('size', 10000)
        result = self.query(*args, **kargs)
        total = result.total
        for offset in range(size, total, size):
            kargs['from_'] = offset
            result2 = self.query(*args, **kargs)
            result.hits += result2.hits

        return result


    def add_articles(self, article_ids, batch_size = 1000):
        """
        Add the given article_ids to the index. This is done in batches, so there
        is no limit on the length of article_ids (which can be a generator).
        """
        if not article_ids: return
        from amcat.models import Article, ArticleSetArticle
        n = len(article_ids) / batch_size
        for i, batch in enumerate(splitlist(article_ids, itemsperbatch=batch_size)):
            log.info("Adding batch {i}/{n}".format(**locals()))
            all_sets = multidict((aa.article_id, aa.articleset_id)
                                 for aa in ArticleSetArticle.objects.filter(article__in=batch))
            dicts = (get_article_dict(article, list(all_sets.get(article.id, [])))
                     for article in Article.objects.filter(pk__in=batch))
            self.bulk_insert(dicts)

    def remove_from_set(self, setid, article_ids, flush=True):
        """Remove the given articles from the given set. This is done in batches, so there
        is no limit on the length of article_ids (which can be a generator)."""
        if not article_ids: return
        for batch in splitlist(article_ids, itemsperbatch=1000):
            self.bulk_update(batch, UPDATE_SCRIPT_REMOVE_FROM_SET, params={'set' : setid})

    def add_to_set(self, setid, article_ids, monitor=NullMonitor()):
        """Add the given articles to the given set. This is done in batches, so there
        is no limit on the length of article_ids (which can be a generator)."""
        if not article_ids: return
        batches = list(splitlist(article_ids, itemsperbatch=1000))
        nbatches = len(batches)
        for i, batch in enumerate(batches):
            monitor.update(40/nbatches, "Added batch {iplus}/{nbatches}".format(iplus=i+1, **locals()))
            self.bulk_update(article_ids, UPDATE_SCRIPT_ADD_TO_SET, params={'set' : setid})

    def bulk_insert(self, dicts):
        """
        Add the given article dict objects to the index using a bulk insert call
        """
        def get_bulk_body(dicts):
            for article_dict in dicts:
                yield serialize(dict(index={'_id' : article_dict['id']}))
                yield serialize(article_dict)
        r = self.es.bulk(body=get_bulk_body(dicts), index=self.index, doc_type=settings.ES_ARTICLE_DOCTYPE)


    def bulk_update(self, article_ids, script, params):
        """
        Execute a bulk update script with the given params on the given article ids.
        """
        payload = serialize(dict(script=script, params=params))
        def get_bulk_body(article_ids, payload):
            for aid in article_ids:
                yield serialize(dict(update={'_id': aid}))
                yield payload
        body = ("\n".join(get_bulk_body(article_ids, payload))) + "\n"
        r = self.es.bulk(body=body, index=self.index, doc_type=settings.ES_ARTICLE_DOCTYPE)

    def synchronize_articleset(self, aset, full_refresh=False):
        """
        Make sure the given article set is correctly stored in the index
        @param full_refresh: if true, re-add all articles to the index. Use this
                             after changing properties of articles
        """
        self.check_index() # make sure index exists and is at least 'yellow'

        log.debug("Getting SOLR ids from set")
        solr_set_ids = set(self.query_ids(filters=dict(sets=aset.id)))
        log.debug("Getting DB ids")
        db_ids = aset.get_article_ids()
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

        log.info("Removing {} articles".format(len(to_remove)))
        self.remove_from_set(aset.id, to_remove)
        log.info("Adding {} articles to set".format(len(to_add_set)))
        self.add_to_set(aset.id, to_add_set)
        log.info("Adding {} articles to index".format(len(to_add_docs)))
        self.add_articles(to_add_docs)
        log.info("Flushing")
        self.flush()

    def count(self, query=None, filters=None):
        """
        Compute the number of items matching the given query / filter
        """
        filters=dict(build_body(query, filters, query_as_filter=True))
        body = {"query" : {"constant_score" : filters}}
        result = self.es.count(index=self.index, doc_type=settings.ES_ARTICLE_DOCTYPE, body=body)
        return result["count"]

    def search_aggregate(self, aggregation, query=None, filters=None):
        """
        Run an aggregate search query and return the aggregation results
        @param aggregation: raw elastic query, e.g. {"terms" : {"field" : "medium"}}
        """
        body = dict(query={"filtered": dict(build_body(query, filters, query_as_filter=True))},
                    aggregations={"aggregation": aggregation})
        result = self.search(body, size=0, search_type="count")
        return result['aggregations']['aggregation']

    def aggregate_query(self, query=None, filters=None, group_by=None, date_interval='month', stats=None):
        """
        Compute an aggregate query, e.g. select count(*) where <filters> group by <group_by>
        If date is used as a group_by variable, uses date_interval to bin it
        Currently, group by must be a single field as elastic doesn't support multiple group by
        (Note: this should be possible in elastic now)
        @param stats: if given, return stats objects for that field (min, max, count, sum) instead of count
        """
        date = group_by == 'date'
        if date:
            aggregation = {'date_histogram': {'field': group_by, 'interval': date_interval}}
        else:
            aggregation = {'terms': {'size': 999999, 'field': group_by}}
        if stats:
            aggregation['aggregations'] = {'statistics': {"stats": {"field": stats}}}

        result = self.search_aggregate(aggregation, query=query, filters=filters)
        for bucket in result['buckets']:
            key, val = bucket['key'], bucket['doc_count']
            if date:
                key = get_date(key)
            if stats:
                val = Result.from_stats(bucket['statistics'], date=date, ntotal=val)
            yield key, val

    def statistics(self, query=None, filters=None):
        """
        Compute and return a Result object with n, start_date and end_date for the selection
        """
        stats = self.search_aggregate({'stats' : {'field' : 'date'}}, query=query, filters=filters)
        return Result.from_stats(stats, date=True)


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
            result = self.es.mget(index=self.index, doc_type=settings.ES_ARTICLE_DOCTYPE,
                                  body={"ids": batch}, fields=[])
            for doc in result['docs']:
                if doc['found']: yield int(doc['_id'])

    def duplicate_exists(self, article):
        """
        Check whether a duplicate of the given article already exists.
        If so, returns the sets that the duplicate is a member of.
        Duplication is checked using de get_hash function, so article
        should be an object with the appropriate attributes (.headline etc)
        @return: A (possibly empty) sequence of results with .id and .sets
        """
        hash = get_article_dict(article).hash
        return self.query(filters={'hashes' : hash}, fields=["sets"], score=False)

    def find_occurrences(self, query, article):
        """
        Find the occurrences of the query in the article (id)
        @return: a sequence of (offset, word) pairs
        """
        if not isinstance(article, int):
            article = article.id
        # get highlighted text
        hl = self.highlight_article(article, query)
        if not (hl and 'text' in hl):
            return
        text = hl['text']

        # parse highlight to return offsets
        pre_tag, post_tag = "<em>", "</em>"
        in_tag = False
        offset = 0
        for token in re.split("({pre_tag}|{post_tag})".format(**locals()), text):
            if token == pre_tag:
                if in_tag:
                    raise ValueError("Encountered pre_tag while in tag")
                in_tag = True
            elif token == post_tag:
                if not in_tag:
                    raise ValueError("Encountered post_tag while not in tag")
                in_tag = False
            else:
                if in_tag:
                    yield offset, token
                offset += len(token)

def get_date(timestamp):
    d = datetime.fromtimestamp(timestamp/1000)
    return datetime(d.year, d.month, d.day)

def get_filter_clauses(start_date=None, end_date=None, on_date=None, **filters):
    """
    Build a elastic DSL query from the 'form' fields.
    For convenience, the singular versions (mediumid, id) etc are allowed as aliases
    """

    def _list(x):
        if isinstance(x, (str, unicode, int)):
            return [int(x)]
        elif hasattr(x, 'pk'):
            return [x.pk]
        return x

    def parse_date(d):
        if isinstance(d, list) and len(d) == 1:
            d = d[0]
        if isinstance(d, (str, unicode)):
            d = toolkit.readDate(d)
        return d.isoformat()

    # Allow singulars as alias for plurals
    f = {}
    for singular, plural in [("mediumid", "mediumids"),
                             ("id", "ids"),
                             ("set", "sets"),
                             ("hash", "hashes")]:
        if plural in filters:
            if singular in filters:
                raise TypeError("Cannot supply both {plural} and {singular}".format(**locals()))
            f[singular] = filters.pop(plural)
        elif singular in filters:
            f[singular] = filters.pop(singular)

    if filters:
        raise TypeError("Unknown filter keywords: {filters}".format(**locals()))

    if 'set' in f: yield dict(terms={'sets' : _list(f['set'])})
    if 'mediumid' in f: yield dict(terms={'mediumid' : _list(f['mediumid'])})
    if 'id' in f: yield dict(ids={'values' : _list(f['id'])})

    date_range = {}
    if start_date: date_range['gte'] = parse_date(start_date)
    if end_date: date_range['lt'] = parse_date(end_date)
    if date_range: yield dict(range={'date' : date_range})

    if 'hash' in f:
        hashes = f['hash']
        if isinstance(hashes, str): hashes = [hashes]
        yield dict(terms={'hash': hashes})

def combine_filters(filters):
    if len(filters) == 0:
        return None
    elif len(filters) == 1:
        return filters[0]
    else:
        return {'bool' : {'must' : filters}}

def build_filter(*args, **kargs):
    filters = list(get_filter_clauses(*args, **kargs))
    return combine_filters(filters)

def build_body(query=None, filters={}, query_as_filter=False):
    """
    Construct the query body from the query and/or filter(s)
    (call with dict(build_body)
    @param query: a elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
    @param filter: field filter DSL query dict, defaults to build_filter(**filters)
    @param query_as_filter: if True, use the query as a filter (faster but not score/relevance)
    """
    filters = list(get_filter_clauses(**filters))
    if query:
        terms = queryparser.parse_to_terms(query)
        if query_as_filter:
            filters.append(terms.get_filter_dsl())
        else:
            yield ('query', terms.get_dsl())

    if filters:
        yield ('filter', combine_filters(filters))


if __name__ == '__main__':
    ES().check_index()

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
from unittest import skipUnless, skip

class TestAmcatES(amcattest.AmCATTestCase):

    @amcattest.use_elastic
    def test_aggregate(self):
        """Can we make tables per medium/date interval?"""
        from amcat.models import Article
        m1 = amcattest.create_test_medium(name="De Nep-Krant")
        m2, m3 = [amcattest.create_test_medium() for _ in range(2)]
        s1 = amcattest.create_test_set()
        s2 = amcattest.create_test_set()
        unused = amcattest.create_test_article(text='aap noot mies', medium=m3, articleset=s2)
        a = amcattest.create_test_article(text='aap noot mies', medium=m1, date='2001-01-01', create=False)
        b = amcattest.create_test_article(text='noot mies wim zus', medium=m2, date='2001-02-01', create=False)
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', medium=m2, date='2002-01-01', create=False)
        d = amcattest.create_test_article(text='noot mies wim zus', medium=m2, date='2001-02-03', create=False)

        Article.create_articles([a,b,c,d], articleset=s1, check_duplicate=False, create_id=True)
        ES().flush()

        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="mediumid")),
                         {m1.id : 1, m2.id : 3})

        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="date", date_interval="year")),
                         {datetime(2001,1,1) : 3, datetime(2002,1,1) : 1})

        self.assertEqual(dict(ES().aggregate_query(filters=dict(sets=s1.id), group_by="date", date_interval="month")),
                         {datetime(2001,1,1) : 1, datetime(2002,1,1) : 1, datetime(2001,2,1) : 2})

        # set statistics
        stats = ES().statistics(filters=dict(sets=s1.id))
        self.assertEqual(stats.count, 4)
        self.assertEqual(stats.min, datetime(2001,1,1))
        self.assertEqual(stats.max, datetime(2002,1,1))

        # media list
        self.assertEqual(set(ES().list_media(filters=dict(sets=s1.id))),
                         {m1.id, m2.id})

    @amcattest.use_elastic
    def test_list_media(self):
        """Test that list media works for more than 10 media"""
        from amcat.models import Article
        media =  [amcattest.create_test_medium() for _ in range(20)]
        arts = [amcattest.create_test_article(medium=m, create=False) for m in media]

        s1 = amcattest.create_test_set()
        Article.create_articles(arts[:5], articleset=s1, check_duplicate=False, create_id=True)
        ES().flush()
        self.assertEqual(set(s1.get_mediums()), set(media[:5]))

        s2 = amcattest.create_test_set(project=s1.project)
        Article.create_articles(arts[5:], articleset=s2, check_duplicate=False, create_id=True)
        ES().flush()
        self.assertEqual(set(s2.get_mediums()), set(media[5:]))

        self.assertEqual(set(s1.project.get_mediums()), set(media))


    @amcattest.use_elastic
    def test_query_all(self):
        """Test that query_all works"""
        from amcat.models import Article
        arts = [amcattest.create_test_article(create=False) for _ in range(20)]
        s = amcattest.create_test_set()
        Article.create_articles(arts, articleset=s, check_duplicate=False, create_id=True)
        ES().flush()

        r = ES().query(filters=dict(sets=s.id), size=10)
        self.assertEqual(len(list(r)), 10)

        r = ES().query_all(filters=dict(sets=s.id), size=10)
        self.assertEqual(len(list(r)), len(arts))




    @amcattest.use_elastic
    def test_filters(self):
        """
        Do filters work properly?
        """
        m1, m2 = [amcattest.create_test_medium() for _ in range(2)]
        a = amcattest.create_test_article(text='aap noot mies', medium=m1, date="2001-01-01")
        b = amcattest.create_test_article(text='noot mies wim zus', medium=m2, date="2002-01-01")
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', medium=m2, date="2003-01-01")

        s1 = amcattest.create_test_set(articles=[a,b,c])
        s2 = amcattest.create_test_set(articles=[a,b])
        ES().flush()

        q = lambda **filters: set(ES().query_ids(filters=filters))

        # MEDIUM FILTER
        self.assertEqual(q(mediumid=m2.id), {b.id, c.id})

        #### DATE FILTERS
        self.assertEqual(q(sets=s1.id, start_date='2001-06-01'), {b.id, c.id})
        # start is inclusive
        self.assertEqual(q(sets=s1.id, start_date='2002-01-01', end_date="2002-06-01"), {b.id})
        # end is exclusive
        self.assertEqual(q(sets=s1.id, start_date='2001-01-01', end_date="2003-01-01"), {a.id, b.id})

        # COMBINATION
        self.assertEqual(q(sets=s2.id, start_date='2001-06-01'), {b.id})
        self.assertEqual(q(end_date='2002-06-01', mediumid=m2.id), {b.id})

    @amcattest.use_elastic
    def test_query(self):
        "Do query and query_ids work properly?"
        a = amcattest.create_test_article(headline="bla", text="artikel artikel een", date="2001-01-01")
        ES().flush()
        print(list(ES().query("een", fields=["date", "headline"])))
        es_a, = ES().query("een", fields=["date", "headline"])
        self.assertEqual(es_a.headline, "bla")
        self.assertEqual(es_a.id, a.id)
        ids = set(ES().query_ids(filters=dict(mediumid=a.medium_id)))
        self.assertEqual(ids, {a.id})


    @amcattest.use_elastic
    def test_articlesets(self):
        a, b, c = [amcattest.create_test_article() for _x in range(3)]
        s1 = amcattest.create_test_set(articles=[a,b,c])
        s2 = amcattest.create_test_set(articles=[b,c])
        s3 = amcattest.create_test_set(articles=[b])
        ES().add_articles([a.id,b.id,c.id])
        ES().flush()

        es_c = ES().get(c.id)
        self.assertEqual(set(es_c['sets']), {s1.id, s2.id})

        ids = ES().query_ids(filters=dict(sets=s1.id))
        self.assertEqual(set(ids), {a.id, b.id, c.id})

    @amcattest.use_elastic
    def test_refresh_index(self):
        """Are added/removed articles added/removed from the index?"""
        # TODO add/remove articles adds to index automatically (does remove?)
        # so refresh isn't really used. Rewrite to add to db manually
        s = amcattest.create_test_set()
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
        s2.remove_articles([a])
        s2.refresh_index()
        self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s2.id))))
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s.id))))



        s.remove_articles([a])
        self.assertEqual({a.id}, set(ES().query_ids(filters=dict(sets=s.id))))
        s.refresh_index()
        self.assertEqual(set(), set(ES().query_ids(filters=dict(sets=s.id))))

        # test that remove from index works for larger sets
        s = amcattest.create_test_set()
        arts = [amcattest.create_test_article(medium=a.medium) for i in range(20)]
        s.add(*arts)

        s.refresh_index()
        solr_ids = set(ES().query_ids(filters=dict(sets=s.id)))
        self.assertEqual(set(solr_ids), {a.id for a in arts})

        s.remove_articles([arts[0]])
        s.remove_articles([arts[-1]])
        s.refresh_index()
        solr_ids = set(ES().query_ids(filters=dict(sets=s.id)))
        self.assertEqual(set(solr_ids), {a.id for a in arts[1:-1]})

        # test that changing an article's properties can be reindexed
        arts[1].medium = amcattest.create_test_medium()
        arts[1].save()


    @amcattest.use_elastic
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

    @amcattest.use_elastic
    def test_scores(self):
        "test if scores (and matches) are as expected for various queries"
        s = amcattest.create_test_set(articles=[
                amcattest.create_test_article(headline="a", text='dit is een test'),
                ])

        s.refresh_index()
        def q(query):
            result = ES().query(query, filters={'sets':s.id}, fields=["headline"])
            return {a.headline : a.score for a in result}

        self.assertEqual(q("test"), {"a" : 1})

        m1, m2 = [amcattest.create_test_medium() for _ in range(2)]
        a = amcattest.create_test_article(text='aap noot mies', medium=m1)
        b = amcattest.create_test_article(text='noot mies wim zus', medium=m2)
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet', medium=m2)
        d = amcattest.create_test_article(text='ik woon in een sociale huurwoning, net als anderen', medium=m2)
        ES().add_articles([a.id, b.id, c.id, d.id])
        ES().flush()

        self.assertEqual(set(ES().query_ids("no*")), {a.id, b.id})
        self.assertEqual(set(ES().query_ids("no*", filters=dict(mediumid=m2.id))), {b.id})
        self.assertEqual(set(ES().query_ids("zus AND jet", filters=dict(mediumid=m2.id))), {c.id})
        self.assertEqual(set(ES().query_ids("zus OR jet", filters=dict(mediumid=m2.id))), {b.id, c.id})
        self.assertEqual(set(ES().query_ids('"mies wim"', filters=dict(mediumid=m2.id))), {b.id})
        self.assertEqual(set(ES().query_ids('"mies wim"~5', filters=dict(mediumid=m2.id))), {b.id, c.id})

        self.assertEqual(set(ES().query_ids('"sociale huur*"', filters=dict(mediumid=m2.id))), {d.id})
        self.assertEqual(set(ES().query_ids('"sociale huur*"', filters=dict(mediumid=m2.id))), {d.id})


    @skip("ComplexPhraseQueryParser does not work for elastic")
    def test_complex_phrase_query(self):
        """Test complex phrase queries. DOES NOT WORK YET"""
        a = amcattest.create_test_article(text='aap noot mies')
        b = amcattest.create_test_article(text='noot mies wim zus')
        c = amcattest.create_test_article(text='mies bla bla bla wim zus jet')
        s1 = amcattest.create_test_set(articles=[a,b,c])
        ES().add_articles([a.id, b.id, c.id])
        self.assertEqual(set(ES().query_ids('"mi* wi*"~5', filters=dict(sets=s1.id))), {b.id, c.id})


    @amcattest.use_elastic
    def test_tokenizer(self):
        text = u"Rutte's Fu\xdf.d66,  50plus, 50+, el ni\xf1o, kanji (\u6f22\u5b57) en Noord-Korea"
        a = amcattest.create_test_article(headline="test", text=text)
        s1 = amcattest.create_test_set(articles=[a])
        ES().add_articles([a.id])
        ES().flush()
        self.assertEqual(set(ES().query_ids("kanji", filters=dict(sets=s1.id))), {a.id})
        self.assertEqual(set(ES().query_ids("blablabla", filters=dict(sets=s1.id))), set())

        # test noord-korea --> noord korea
        self.assertEqual(set(ES().query_ids("korea", filters=dict(sets=s1.id))), {a.id})
        self.assertEqual(set(ES().query_ids('"korea-noord"', filters=dict(sets=s1.id))), set())
        self.assertEqual(set(ES().query_ids('"noord-korea"', filters=dict(sets=s1.id))), {a.id})

        # test Rutte's -> rutte s
        self.assertEqual(set(ES().query_ids("rutte", filters=dict(sets=s1.id))), {a.id})
        self.assertEqual(set(ES().query_ids("Rutte", filters=dict(sets=s1.id))), {a.id})

        # test ni\~no -> nino
        self.assertEqual(set(ES().query_ids("nino", filters=dict(sets=s1.id))), {a.id})
        self.assertEqual(set(ES().query_ids(u"ni\xf1o", filters=dict(sets=s1.id))), {a.id})

        # test real kanji
        self.assertEqual(set(ES().query_ids(u"\u6f22\u5b57", filters=dict(sets=s1.id))), {a.id})

    @amcattest.use_elastic
    def test_byline(self):
        aset = amcattest.create_test_set()
        amcattest.create_test_article(byline="bob", text="eve", articleset=aset)

        ES().flush()

        q = lambda query: set(ES().query_ids(query, filters={"sets": aset.id}))

        self.assertEqual(1, len(q("byline:bob")))
        self.assertEqual(0, len(q("byline:eve")))
        self.assertEqual(1, len(q("bob")))
