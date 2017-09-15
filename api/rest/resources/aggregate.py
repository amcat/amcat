import math

from django.conf.urls import patterns, url
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.fields import DateField, CharField, IntegerField
from rest_framework.serializers import Serializer
from amcat.tools import amcates, keywordsearch
from api.rest.resources.amcatresource import AmCATResource
from django_filters import filters, filterset
from amcat.tools.caching import cached
import itertools, collections
from amcat.models import Medium

DATES = ['year','quarter','month','week','day']
FILTER_FIELDS = "start_date","end_date","mediumid","ids","sets","insertscript"

#TODO: Copypasta: AggregateES/lazyES and AggregateResource/SearchResource should share common ancestors

class AggregateES(object):
    def __init__(self, axes, queries=None, filters=None, stats=None):
        self.queries = queries
        self.filters = filters or {}
        self.es = amcates.ES()
        self.axes = axes
        self.stats = stats

    def output(self, n, *fields):
        result = dict(zip(self.axes, fields))
        if type(n) == int:
            result["count"] = n
        else:
            result.update(n.__dict__)
            #result.update(dict(zip(self.axes, fields)))
        return result

    @property
    def query(self):
        if self.queries:
            return "\n".join("({q.query})".format(**locals()) for q in self.queries)

    def filter(self, key, value):
        self.filters[key] = value

    def _get_results(self):
        if not self.axes:
            # give raw count
            yield {"count" : self.es.count(query=self.query, filters=self.filters)}
            return

        if len(self.axes) > 2: raise NotImplementedError("Aggregation on >2 axes currently not supported")

        x = self.axes[0]
        y = None if len(self.axes) == 1 else self.axes[1]
        if x == "hits": raise NotImplementedError("Hits can currently only be used as axes2. Sorry!")
        if y is None:
            for (group, n) in self._get_counts(x):
                yield self.output(n, group)
        elif y in ("mediumid","medium"):
            medium_ids = self.es.list_media(self.query, self.filters)
            if y == "medium":
                medium_ids = list(medium_ids)
                media = {pk: name for (pk, name)
                         in Medium.objects.filter(pk__in=medium_ids).values_list("pk", "name")}
            for medium_id in medium_ids:
                medium = media[medium_id] if y == "medium" else medium_id
                for group, n in self._get_counts(x, mediumid=medium_id):
                    yield self.output(n, group, medium)
        elif y == "query":
            if not self.queries:
                raise ValueError("Please specify at least one query (using q=) when aggregating on query")
            for q in self.queries:
                for group, n in self._get_counts(x, query=q.query):
                    yield self.output(n, group, q.label)

        else:
            raise ValueError("Cannot aggregate on axes2="+y)



    def _get_counts(self, axis, query=None, **extra_filters):
        if axis in DATES:
            interval = axis
            axis = 'date'
        else:
            interval=None

        if query is None: query = self.query

        filters = self.filters.copy()
        filters.update(extra_filters)
        return self.es.aggregate_query(query, filters, axis, interval, stats=self.stats)

    @property
    @cached
    def result(self):
        return list(self._get_results())

    def __len__(self):
        return len(self.result)

    def __getitem__(self, i):
        return self.result[i]

class AggregateResource(AmCATResource):

    @property
    @cached
    def axes(self):
        params = self.request.QUERY_PARAMS or self.request.DATA
        axes = ("axis{i}".format(**locals()) for i in itertools.count(1))
        return [params[x] for x in itertools.takewhile(params.__contains__, axes)]

    @property
    @cached
    def queries(self):
        params = self.request.QUERY_PARAMS or self.request.DATA
        return [keywordsearch.SearchQuery.from_string(q)
                for q in params.getlist("q")]

    @property
    @cached
    def stats(self):
        params = self.request.QUERY_PARAMS or self.request.DATA
        return params.get('stats')

    def get_queryset(self):
        return AggregateES(self.axes, self.queries, stats=self.stats)

    def filter_queryset(self, queryset):
        params = self.request.QUERY_PARAMS or self.request.DATA
        for k in FILTER_FIELDS:
            if k in params:
                queryset.filter(k, params.getlist(k))
        return queryset

    @classmethod
    def get_model_name(cls):
        return "aggregate"

    def get_serializer_context(self):
        ctx = super(AggregateResource, self).get_serializer_context()
        ctx["axes"] = self.axes
        ctx['stats'] = self.stats
        return ctx

    def post(self, request, *args, **kwargs):
        # allow for POST requests
        return self.list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        try:
            return super(AggregateResource, self).list(request, *args, **kwargs)
        except Exception, e:
            from rest_framework.exceptions import APIException
            raise APIException(str(e))

        
    class serializer_class(Serializer):
        count = IntegerField()

        def __init__(self, *args, **kwargs):
            Serializer.__init__(self, *args, **kwargs)
            for x in kwargs["context"]["axes"]:
                self.fields[x] = CharField()
            if kwargs['context']['stats']:
                for field in "min", "max":
                    self.fields[field] = IntegerField()
