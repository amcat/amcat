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

import datetime
import functools
import logging
import os
import re
from collections import namedtuple
from hashlib import sha224 as hash_class
from json import dumps as serialize
from typing import Union

from django.conf import settings
from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import scan, bulk

from amcat.tools import queryparser, toolkit
from amcat.tools.caching import cached
from amcat.tools.progress import ProgressMonitor
from amcat.tools.toolkit import multidict, splitlist

log = logging.getLogger(__name__)

_clean_re = re.compile('[\x00-\x08\x0B\x0C\x0E-\x1F]')
def _clean(s):
    """Remove non-printable characters and convert dates"""
    if isinstance(s, str):
        s = _clean_re.sub(' ', s)
    if isinstance(s, datetime.date):
        s = datetime.datetime(s.year, s.month, s.day)
    if isinstance(s, (datetime.date, datetime.datetime)):
        s = s.isoformat()
    return s

ARTICLE_FIELDS = frozenset({"text", "title", "url", "date", "parent_hash"})
ALL_FIELDS = frozenset({"id", "sets", "hash"} | ARTICLE_FIELDS)

RE_PROPERTY_NAME = re.compile('[A-Za-z][A-Za-z0-9]*$')

_KNOWN_PROPERTIES = None


@functools.lru_cache()
def get_property_primitive_type(name) -> Union[int, float, str, datetime.datetime]:
    """Based on a property name, determine its primitive Python type."""
    if "_" in name:
        return settings.ES_MAPPING_TYPE_PRIMITIVES[name[name.rfind("_")+1:]]

    # Return type specified in ES_MAPPING
    if name in settings.ES_MAPPING["properties"]:
        for ptype, obj in settings.ES_MAPPING_TYPES.items():
            if settings.ES_MAPPING["properties"][name] is obj:
                return settings.ES_MAPPING_TYPE_PRIMITIVES[ptype]

    # No type in name nor a 'special' field
    return settings.ES_MAPPING_TYPE_PRIMITIVES["default"]


def _is_valid_property_name(name: str) -> bool:
    if not isinstance(name, str):
        raise ValueError("property name should be a string")

    if "_" in name:
        name, ptype = name.rsplit("_", 1)
        if not ptype in settings.ES_MAPPING_TYPES:
            return False
    return bool(RE_PROPERTY_NAME.match(name))


def get_properties(article):
    if article.properties:
        if not isinstance(article.properties, dict):
            raise TypeError("Article properties should be a simple key:value dict")
        for k, v in article.properties.items():
            if not _is_valid_property_name(k):
                raise TypeError("Article properties should be a simple key:value dict")
            if not isinstance(v, (str, int, float, datetime.datetime, datetime.date)):
                raise TypeError("Article properties should be a simple key:value dict")
            if k in ALL_FIELDS:
                raise ValueError("Article properties cannot duplicate built-in properties")
            yield k, _clean(v)
                              

def get_article_dict(article, sets=None):
    d = {field_name: _clean(getattr(article, field_name))
         for field_name in ARTICLE_FIELDS}   
    d.update(get_properties(article))
    d['hash'] = _hash_dict(d)
    d['id'] = article.id
    d["sets"] = sets
    return d

def _escape_bytes(b):
    return b.replace(b"\\", b"\\\\").replace(b",", b"\\,")

def _hash_dict(d):
    c = hash_class()
    for fn in sorted(d.keys()):
        c.update(_escape_bytes(_encode_field(fn)))
        c.update(_escape_bytes(_encode_field(d[fn])))
        c.update(b",")
    return c.hexdigest()

def _encode_field(object, encoding="utf-8"):
    if isinstance(object, datetime.datetime):
        return object.isoformat().encode(encoding)
    return str(object).encode(encoding)


HIGHLIGHT_OPTIONS = {
    'pre_tags': ['<mark>'],
    'post_tags': ['</mark>'],
    'fields': {
        'text': {
            "fragment_size": 100,
            "number_of_fragments": 3,
            'no_match_size': 100
        },
        'title': {
            'no_match_size': 100 
        }
    }
}

LEAD_SCRIPT_FIELD = {"lead": {"script": r"if (_source['text']) _source['text'].replace('\r', '').split('\n\n')[0]"}}

UPDATE_SCRIPT_REMOVE_FROM_SET = ("s=ctx._source; "
                                 "if (s.sets) {s.sets -= set}")

UPDATE_SCRIPT_ADD_TO_SET = ("s=ctx._source; "
                            "if (s.sets) {if (!(set in s.sets)) s.sets += set} "
                            "else {s.sets = [set]}")

def _get_bulk_body(articles, action):
    for article_id, article in articles.items():
        yield serialize({action: {'_id': article_id}})
        yield article

def get_bulk_body(articles, action="index"):
    return "\n".join(_get_bulk_body(articles, action)) + "\n"

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
        """Return the results as fieldname : value dicts"""
        return [r.__dict__ for r in self]

class Result(object):
    """Simple class to hold arbitrary values"""

    @classmethod
    def from_hit(cls, searchresult, row, fields, score=True):
        """@param hit: elasticsearch hit dict"""
        field_dict = {f: None for f in fields}
        if 'fields' in row:
            for (k, v) in row['fields'].items():
                if k != "sets":
                    # elastic 1.0 always returns arrays, we only want
                    # sets in a list, the rest should be 'scalarized'
                    if isinstance(v, list):
                        v = v[0]
                field_dict[k] = v

        result = Result(id=int(row['_id']), _searchresult=searchresult, **field_dict)
        if score: result.score = int(row['_score'])
        if 'highlight' in row: result.highlight = row['highlight']
        if hasattr(result, 'date'):
            if len(result.date) == 10:
                result.date = datetime.datetime.strptime(result.date, '%Y-%m-%d')
            else:
                result.date = datetime.datetime.strptime(result.date[:19], '%Y-%m-%dT%H:%M:%S')
        return result

    @classmethod
    def from_stats(cls, stats, date=False, **kargs):
        """Create a Result object from an ES statistics dict {u'count': 0, u'max': ...}"""
        result = Result(**kargs)
        result.count = stats['count']
        if result.count == 0:
            result.start_date, result.end_date = None, None
        else:
            f = get_date if date else int
            result.min=f(stats['min'])
            result.max=f(stats['max'])
        return result

    def to_dict(self):
        return dict(self._result)

    def __init__(self, **kwargs):
        self._result = kwargs
        self.__dict__.update(kwargs)

    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))

def get_highlight_query(query, fieldname):
    query = queryparser.parse(query, fieldname)
    return {"highlight_query": query, "number_of_fragments": 0}

def delete_test_indices():
    es = ES()
    indices = es.es.indices.get_aliases().keys()
    test_indices = filter(lambda i: i.startswith("test_"), indices)
    for test_index in test_indices:
        ES(index=test_index).delete_index()


class ElasticSearchError(Exception):
    pass

class ES(object):
    def __init__(self, index=None, doc_type=None, timeout=300, **args):
        elhost = {"host":settings.ES_HOST, "port":settings.ES_PORT}
        self.es = Elasticsearch(hosts=[elhost, ], timeout=timeout, **args)
        self.index = settings.ES_INDEX if index is None else index
        self.doc_type = settings.ES_ARTICLE_DOCTYPE if doc_type is None else doc_type

        if settings.TESTING and index is None:
            self.index += "_{pid}".format(pid=os.getpid())

    def check_properties(self, properties):
        """
        Check if all properties are known (e.g. have mappings), and creates mappings as needed
        """
        properties = set(properties)
        if not (properties - self.get_properties()):
            return
        to_add = properties - self.get_properties(force_refresh=True)
        if to_add:
            self.add_properties(to_add)

    def add_properties(self, to_add):
        """
        Add the named properties, setting mapping depending on suffix
        """
        mappings = {}
        for name in to_add:
            ftype = name.rsplit("_", 1)[1] if "_" in name else 'default'
            mappings[name] = settings.ES_MAPPING_TYPES[ftype]
        self.es.indices.put_mapping(index=self.index, doc_type=self.doc_type,
                                    body={"properties": mappings})

    def get_mapping(self):
        m = self.es.indices.get_mapping(self.index, self.doc_type)
        return m[self.index]['mappings'][self.doc_type]['properties']
        
    def get_properties(self, force_refresh=False):
        global _KNOWN_PROPERTIES
        if force_refresh or (_KNOWN_PROPERTIES is None):
            _KNOWN_PROPERTIES = set(self.get_mapping().keys())
        return _KNOWN_PROPERTIES
            
    def flush(self):
        self.es.indices.flush()

    def highlight_article(self, aid, query):
        body = {
            'filter': build_filter(ids=aid),
            'highlight': {
                "fields": {
                    "text": get_highlight_query(query, "text"),
                    "title": get_highlight_query(query, "title"),
                    "byline": get_highlight_query(query, "byline"),
                }
            }
        }

        result = self.search(body, fields=[])
        hits = result['hits']['hits'][0].get("highlight", {})
        return {f: hits[f][0] for f in hits}

    def clear_cache(self):
        self.es.indices.clear_cache()

    def delete_index(self):
        try:
            self.es.indices.delete(self.index)
        except NotFoundError:
            pass
        except Exception as e:
            if 'IndexMissingException' in str(e):
                return
            raise

    def create_index(self, shards=5, replicas=1):
        es_settings = settings.ES_SETTINGS.copy()
        es_settings.update({"number_of_shards" : shards,
                            "number_of_replicas": replicas})

        body = {
            "settings": es_settings,
            "mappings": {
                settings.ES_ARTICLE_DOCTYPE: settings.ES_MAPPING
            }
        }

        self.es.indices.create(self.index, body)

    def check_index(self):
        """
        Check whether the server is up and the index exists.
        If the server is down, raise an exception.
        If the index does not exist, try to create it.
        """
        if not self.es.ping():
            raise Exception("Elastic server cannot be reached")
        if not self.es.indices.exists(self.index):
            log.info("Index {self.index} does not exist, creating".format(**locals()))
            self.create_index()
        return self.es.cluster.health(self.index, wait_for_status='yellow')

    def exists_type(self, doc_type, **kargs):
        return self.es.indices.exists_type(index=self.index, doc_type=doc_type, **kargs)

    def put_mapping(self, doc_type, body, **kargs):
        return self.es.indices.put_mapping(index=self.index, doc_type=doc_type, body=body, **kargs)
        
    def status(self):
        nodes = self.es.nodes.info()['nodes'].values()
        return {"ping": self.es.ping(),
                "nodes": [n['name'] for n in nodes],
                "index": self.index,
                "index_health": self.es.cluster.health(self.index),
                "transport_hosts": self.es.transport.hosts,
            }

    def get(self, id, **options):
        """
        Get a single article from the index
        """
        kargs = dict(index=self.index, doc_type=self.doc_type)
        kargs.update(options)
        return self.es.get_source(id=id, **kargs)

    def mget(self, ids, doc_type=None, parents=None):
        """
        Get multiple articles from the index.
        If paret is given, it should be a sequence of the same length as ids
        """
        if parents is None: parents = [None] * len(ids)
        if doc_type is None: doc_type = self.doc_type
        getdocs = [{"_index" : self.index, "_id" : id, "_parent" : parent, "_type" : doc_type}
                   for (id, parent) in zip(ids, parents)]
        return self.es.mget({"docs": getdocs})['docs']
        
    def search(self, body, **options):
        """
        Perform a 'raw' search on the underlying ES index
        """
        kargs = dict(index=self.index, doc_type=self.doc_type)
        kargs.update(options)
        return self.es.search(body=body, **kargs)

    def scan(self, query, **kargs):
        """
        Perform a scan query on the es index
        See: http://elasticsearch-py.readthedocs.org/en/latest/helpers.html#elasticsearch.helpers.scan
        """
        return scan(self.es, index=self.index, doc_type=self.doc_type, query=query, **kargs)
        
    def query_ids(self, query=None, filters={}, body=None, limit=None, **kwargs):
        """
        Query the index returning a sequence of article ids for the mathced articles

        @param query: a elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
        @param filter: field filter DSL query dict
        @param body: if given, use this instead of constructing from query/filters
        @param filters: if filter is None, build filter from filters as accepted by build_query, e.g. sets=12345

        Note that query and filters can be combined in a single call
        """
        if body is None:
            body = dict(build_body(query, filters, query_as_filter=True))
        for i, a in enumerate(scan(self.es, query=body, index=self.index, doc_type=self.doc_type,
                                   size=(limit or 1000), fields="")):
            if limit and i >= limit:
                return
            yield int(a['_id'])


    def query(self, query=None, filters={}, highlight=False, lead=False, fields=[], score=True, **kwargs):
        """
        Execute a query for the given fields with the given query and filter
        @param query: a elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
        @param filter: field filter DSL query dict, defaults to build_filter(**filters)
        @param kwargs: additional keyword arguments to pass to es.search, eg fields, sort, from_, etc
        @return: a list of named tuples containing id, score, and the requested fields
        """
        body = dict(build_body(query, filters, query_as_filter=(not (highlight or score))))
        if highlight and not score:
            body['query'] = {'constant_score': {'query': body['query']}}

        if 'sort' in kwargs:
            body['track_scores'] = True

        if highlight and query:
            if isinstance(highlight, dict):
                body['highlight'] = highlight
            else:
                body['highlight'] = HIGHLIGHT_OPTIONS
        if lead or False and query == "" and highlight: 
            body['script_fields'] = LEAD_SCRIPT_FIELD

            
        result = self.search(body, fields=fields, **kwargs)
        return SearchResult(result, fields, score, body, query=query)

    def query_all(self, *args, **kargs):
        kargs.update({"from_": 0})
        size = kargs.setdefault('size', 10000)
        result = self.query(*args, **kargs)
        total = result.total
        for offset in range(size, total, size):
            kargs['from_'] = offset
            result2 = self.query(*args, **kargs)
            result.hits += result2.hits

        return result

    def get_used_properties(self, sets):
        """
        Returns a sequency of property names in use in the specified set(s) (or setids)
        """
        sets = [s if isinstance(s, int) else s.id for s in sets]
        for prop in set(self.get_properties(force_refresh=True)) - set(ALL_FIELDS):
            body = {"query": {"bool": {"must": [
                {"terms": {"sets": sets}},
                {"exists": {"field": prop}}]}}}
            n = self.es.count(index=self.index, doc_type=self.doc_type, body=body)['count']
            if n:
                yield prop
                
    def add_articles(self, article_ids, batch_size=1000):
        """
        Add the given article_ids to the index. This is done in batches, so there
        is no limit on the length of article_ids (which can be a generator).
        """
        #WvA: remove redundancy with create_articles
        if not article_ids: return
        from amcat.models import Article, ArticleSetArticle

        n = len(article_ids) / batch_size
        for i, batch in enumerate(splitlist(article_ids, itemsperbatch=batch_size)):
            log.info("Adding batch {i}/{n}".format(**locals()))
            all_sets = multidict((aa.article_id, aa.articleset_id)
                                 for aa in ArticleSetArticle.objects.filter(article__in=batch))
            dicts = (get_article_dict(article, list(all_sets.get(article.id, [])))
                     for article in Article.objects.filter(pk__in=batch))            
            self.bulk_insert(dicts, batch_size=None)

    def remove_from_set(self, setid, article_ids, flush=True):
        """Remove the given articles from the given set. This is done in batches, so there
        is no limit on the length of article_ids (which can be a generator)."""
        if not article_ids: return
        for batch in splitlist(article_ids, itemsperbatch=1000):
            self.bulk_update(batch, UPDATE_SCRIPT_REMOVE_FROM_SET, params={'set': setid})

    def add_to_set(self, setid, article_ids, monitor=ProgressMonitor()):
        """Add the given articles to the given set. This is done in batches, so there
        is no limit on the length of article_ids (which can be a generator)."""
        if not article_ids: return
        batches = list(splitlist(article_ids, itemsperbatch=1000))
        nbatches = len(batches)
        for i, batch in enumerate(batches):
            monitor.update(40/nbatches, "Added batch {iplus}/{nbatches}".format(iplus=i+1, **locals()))
            self.bulk_update(batch, UPDATE_SCRIPT_ADD_TO_SET, params={'set' : setid})

    def term_vector(self, aid, fields=["text", "title"]):

        # elasticsearch client supports term vectors from version 2.0
        # so we do it 'manually' for now:
        from elasticsearch.client.utils import _make_path
        url = _make_path(self.index, settings.ES_ARTICLE_DOCTYPE, aid, "_termvector")
        # I think perform_request tests status code?
        fields = ",".join(fields)
        _, data = self.es.transport.perform_request('GET', url, params={"fields": fields})
        return data
            
    def bulk_insert(self, dicts, batch_size=1000, monitor=ProgressMonitor()):
        """
        Bulk insert the given articles in batches of batch_size
        """
        if batch_size:
            batches = list(toolkit.splitlist(dicts, itemsperbatch=batch_size))
        else:
            batches = [dicts]
        nbatches = len(batches)
        for i, batch in enumerate(batches):
            monitor.update(40/nbatches, "Added batch {iplus}/{nbatches}".format(iplus=i+1, **locals()))
            props, articles = set(), {}
            for d in batch:
                props |= (set(d.keys()) - ALL_FIELDS)
                articles[d["id"]] = serialize(d)

            self.check_properties(props)
            body = get_bulk_body(articles)
            resp = self.es.bulk(body=body, index=self.index, doc_type=settings.ES_ARTICLE_DOCTYPE)
            if resp["errors"]:
                raise ElasticSearchError(resp)
            

    def update_values(self, article_id, values):
        """Update properties of existing article.

        @param values: mapping from field name to (new) value
        @type values: dict"""
        return self.bulk_update_values({article_id: values})

    def bulk_update_values(self, articles):
        """Updates set of articles in bulk.
        """
        body = get_bulk_body({aid: serialize({"doc": a}) for aid, a in articles.items()}, action="update")
        resp = self.es.bulk(body=body, index=self.index, doc_type=settings.ES_ARTICLE_DOCTYPE)

        if resp["errors"]:
            raise ElasticSearchError(resp)

    def bulk_update(self, article_ids, script, params):
        """
        Execute a bulk update script with the given params on the given article ids.
        """
        payload = serialize(dict(script=script, params=params))
        body = get_bulk_body({aid: payload for aid in article_ids}, action="update")
        resp = self.es.bulk(body=body, index=self.index, doc_type=settings.ES_ARTICLE_DOCTYPE)

        if resp["errors"]:
            raise ElasticSearchError(resp)

    def synchronize_articleset(self, aset, full_refresh=False):
        """
        Make sure the given articleset is correctly stored in the index
        @param full_refresh: if true, re-add all articles to the index. Use this
                             after changing properties of articles
        """
        self.check_index()  # make sure index exists and is at least 'yellow'

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
                         nta=len(to_add_docs), ntas=len(to_add_set), ntr=len(to_remove), **locals()))

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
        filters = dict(build_body(query, filters, query_as_filter=True))
        body = {"query": {"constant_score": filters}}
        result = self.es.count(index=self.index, doc_type=settings.ES_ARTICLE_DOCTYPE, body=body)
        return result["count"]

    def search_aggregate(self, aggregation, query=None, filters=None, **options):
        """
        Run an aggregate search query and return the aggregation results
        @param aggregation: raw elastic query, e.g. {"terms" : {"field" : "medium"}}
        """
        body = dict(query={"filtered": dict(build_body(query, filters, query_as_filter=True))},
                    aggregations={"aggregation": aggregation})
        result = self.search(body, size=0, search_type="count", **options)
        return result['aggregations']['aggregation']

    def _parse_terms_aggregate(self, aggregate, group_by, terms, sets):
        if not group_by:
            for term in terms:
                yield term, aggregate[term.label]['doc_count']
        else:
            for term in terms:
                yield term, self._parse_aggregate(aggregate[term.label], list(group_by), terms, sets)

    def _parse_other_aggregate(self, aggregate, group_by, group, terms, sets):
        buckets = aggregate[group]["buckets"]
        if not group_by:
            return ((b['key'], b['doc_count']) for b in buckets)
        return ((b['key'], self._parse_aggregate(b, list(group_by), terms, sets)) for b in buckets)

    def _parse_aggregate(self, aggregate, group_by, terms, sets):
        """Parse a aggregation result to (nested) namedtuples."""
        group = group_by.pop(0)

        if group == "terms":
            result = self._parse_terms_aggregate(aggregate, group_by, terms, sets)
        else:
            result = self._parse_other_aggregate(aggregate, group_by, group, terms, sets)
            if group == "sets" and sets is not None:
                # Filter sets if 'sets' is given
                result = ((aset_id, res) for aset_id, res in result if aset_id in set(sets))
            elif group == "date":
                # Parse timestamps as datetime objects
                result = ((get_date(stamp), aggr) for stamp, aggr in result)

        # Return results as namedtuples
        ntuple = namedtuple("Aggr", [group, "buckets" if group_by else "count"])
        return [ntuple(*r) for r in result]

    def _build_aggregate(self, group_by, date_interval, terms, sets):
        """Build nested aggregation query for list of groups"""
        group = group_by.pop(0)

        if group == 'date':
            aggregation = {
                group: {
                    'date_histogram': {
                        'field': group,
                        'interval': date_interval,
                        "min_doc_count" : 1
                    }
                }
            }
        elif group == 'terms':
            aggregation = {
                term.label: {
                    'filter': dict(build_body(term.query))
                } for term in terms
            }
        else:
            aggregation = {
                group: {
                    'terms': {
                        # Default size is too small, we want to return all results
                        'size': 999999,
                        'field': group
                    }
                }
            }

        # We need to nest the other aggregations, see:
        # http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/search-aggregations.html
        if group_by:
            nested = self._build_aggregate(group_by, date_interval, terms, sets)
            for aggr in aggregation.values():
                aggr["aggregations"] = nested

        return aggregation

    def aggregate_query(self, query=None, filters=None, group_by=None, terms=None, sets=None, date_interval='month'):
        """
        Compute an aggregate query, e.g. select count(*) where <filters> group by <group_by>. If
        date is used as a group_by variable, uses date_interval to bin it. It does support multiple
        values for group_by.

        You can group_by on terms by supplying "terms" to group_by. In addition, you will need to
        supply terms as a parameter, which consists of a list of SearchQuery's. Query is then used
        as a global filter, while terms are 'local'.

        @param query: an elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
        @type group_by: list / tuple
        @type mediums: bool
        @param mediums: return Medium objects, instead of ids
        """
        if isinstance(group_by, str):
            log.warning("Passing strings to aggregate_query(group_by) is deprecated.")
            group_by = [group_by]

        if "terms" in group_by and terms is None:
            raise ValueError("You should pass a list of terms if aggregating on it.")

        filters = dict(build_body(query, filters, query_as_filter=True))
        aggregations = self._build_aggregate(list(group_by), date_interval, terms, sets)

        body = {
            "query": {"constant_score": filters},
            "aggregations": aggregations
        }

        log.debug("es.search(body={body})".format(**locals()))
        result = self.search(body)
        result = self._parse_aggregate(result["aggregations"], list(group_by), terms, sets)
        return result

    def statistics(self, query=None, filters=None):
        """Compute and return a Result object with n, start_date and end_date for the selection"""
        body = {
            "query": {
                "constant_score": dict(
                    build_body(query, filters, query_as_filter=True)
                )
            },
            'aggregations': {
                'stats': {
                    'stats': {'field': 'date'}
                }
            }
        }


        stats = self.search(body, size=0)['aggregations']['stats']
        result = Result()
        result.n = stats['count']
        if result.n == 0:
            result.start_date, result.end_date = None, None
        else:
            result.start_date = get_date(stats['min'])
            result.end_date = get_date(stats['max'])
        return result

    def list_media(self, query=None, filters=None):
        """
        List a sequence of medium_ids that exist in the selection
        """
        from amcat.tools.aggregate_es import aggregate, MediumCategory
        for medium_id, count in aggregate(query, filters, [MediumCategory()], objects=False, es=self):
            yield medium_id

    def list_dates(self, query=None, filters=None, interval="day"):
        from amcat.tools.aggregate_es import aggregate, IntervalCategory
        for date, count in aggregate(query, filters, [IntervalCategory(interval)], es=self):
            yield date

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
        should be an object with the appropriate attributes (.title etc)
        @return: A (possibly empty) sequence of results with .id and .sets
        """
        hash = get_article_dict(article).hash
        return self.query(filters={'hashes': hash}, fields=["sets"], score=False)

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

    def _get_purge_actions(self, query):
        for id in self.query_ids(body=query):
            yield {
                "_op_type": "delete",
                "_id": id,
                "_index": self.index,
                "_type": settings.ES_ARTICLE_DOCTYPE
            }

    def purge_orphans(self):
        """Remove all articles without set from the index"""
        query =  {"query": {"constant_score": {"filter": {"missing": {"field": "sets"}}}}}
        return bulk(self.es, self._get_purge_actions(query))

    def get_child_type_counts(self, **filters):
        """Get the number of child documents per type"""
        filters = dict(build_body(filters=filters))
        filter = {"has_parent": {"parent_type": self.doc_type, "filter": filters['filter']}}
        aggs = {"module": {"terms": {"field": "_type"}}}
        body = {"aggs": {"prep": {"filter": filter, "aggs": aggs}}}
        r = self.es.search(index=self.index, search_type="count", body=body)
        for b in r['aggregations']['prep']['module']['buckets']:
            yield b['key'], b['doc_count']   

    def get_articles_without_child(self, child_doctype, limit=None, **filters):
        """Return the ids of all articles without a child of the given doctype"""
        nochild =  {"not" : {"has_child" : { "type": child_doctype,
                                             "query" : {"match_all" : {}}}}}        
        filter = dict(build_body(filters=filters))['filter']
        body = {"filter": {"bool" : {"must" : [filter, nochild]}}}
        return self.query_ids(body=body, limit=limit)

def get_date(timestamp):
    d = datetime.datetime.fromtimestamp(timestamp / 1000)
    return datetime.datetime(d.year, d.month, d.day)


def get_filter_clauses(start_date=None, end_date=None, on_date=None, **filters):
    """
    Build a elastic DSL query from the 'form' fields.
    For convenience, the singular versions (mediumid, id) etc are allowed as aliases
    """

    def _list(x, number=True):
        if isinstance(x, (str, int)):
            return [int(x) if number else x]
        elif hasattr(x, 'pk'):
            return [x.pk]
        elif isinstance(x, (set, tuple, list)):
            return x
        return list(x)

    def parse_date(d):
        if isinstance(d, list) and len(d) == 1:
            d = d[0]
        if isinstance(d, str):
            d = toolkit.read_date(d)
        return d.isoformat()

    # Allow singulars as alias for plurals
    f = {}
    for singular, plural in [("id", "ids"),
                             ("set", "sets"),
                             ("hash", "hashes")]:
        if plural in filters:
            if singular in filters:
                raise TypeError("Cannot supply both {plural} and {singular}".format(**locals()))
            f[singular] = filters.pop(plural)
        elif singular in filters:
            f[singular] = filters.pop(singular)


    for k, v in filters.items():
        yield {'terms': {k: _list(v, number=False)}}

    if 'set' in f: yield dict(terms={'sets': _list(f['set'])})
    if 'id' in f: yield dict(ids={'values': _list(f['id'])})
    if 'hash' in f: yield dict(terms={'hash' : _list(f['hash'], number=False)})

    date_range = {}
    if start_date: date_range['gte'] = parse_date(start_date)
    if end_date: date_range['lt'] = parse_date(end_date)
    if date_range: yield dict(range={'date': date_range})
    if on_date: date_range={"gte": parse_date(on_date),
                            "lt": parse_date(on_date)+"||+1d"}
    if date_range: yield dict(range={'date' : date_range})


def combine_filters(filters):
    if len(filters) == 0:
        return None
    elif len(filters) == 1:
        return filters[0]
    else:
        return {'bool': {'must': filters}}


def build_filter(*args, **kargs):
    filters = list(get_filter_clauses(*args, **kargs))
    return combine_filters(filters)


def build_body(query=None, filters={}, query_as_filter=False):
    """
    Construct the query body from the query and/or filter(s)
    (call with dict(build_body)
    @param query: an elastic query string (i.e. lucene syntax, e.g. 'piet AND (ja* OR klaas)')
    @param filters: field filter DSL query dict, defaults to build_filter(**filters)
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
# amcat.tools.tests.amcates

