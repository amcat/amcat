import itertools
import collections
from rest_framework.exceptions import ParseError

from rest_framework.fields import CharField, IntegerField
from rest_framework.serializers import Serializer, re

from amcat.tools import amcates, keywordsearch
from amcat.tools.amcates import safe_identifier

from api.rest.resources.amcatresource import AmCATResource
from amcat.tools.caching import cached


DATES = ['year', 'quarter', 'month', 'week', 'day']
FILTER_FIELDS = "start_date", "end_date", "ids", "sets"

# TODO: Copypasta: AggregateES/lazyES and AggregateResource/SearchResource should share common ancestors

class AggregateES(object):
    def __init__(self, axes, queries=None, filters=None):
        self.queries = queries
        self.filters = filters or {}
        self.es = amcates.ES()
        self.axes = axes
        axis_names = [safe_identifier(axis) for axis in axes]
        self.result_type = collections.namedtuple("Result", axis_names + ["count"])

    @property
    def query(self):
        if self.queries:
            return "\n".join("({q.query})".format(**locals()) for q in self.queries)

    def filter(self, key, value):
        self.filters[key] = value

    def _get_results(self):
        if not self.axes:
            # give raw count
            yield {"count": self.es.count(query=self.query, filters=self.filters)}
            return

        if len(self.axes) > 2: raise NotImplementedError("Aggregation on >2 axes currently not supported")

        x = self.axes[0]
        y = None if len(self.axes) == 1 else self.axes[1]
        if x == "hits": raise NotImplementedError("Hits can currently only be used as axes2. Sorry!")
        if y is None:
            for (group, n) in self._get_counts(x):
                yield self.result_type(group, n)
        elif y == "query":
            if not self.queries:
                raise ValueError("Please specify at least one query (using q=) when aggregating on query")
            for q in self.queries:
                for group, n in self._get_counts(x, query=q.query):
                    yield self.result_type(group, q.label, n)

        else:
            raise ValueError("Cannot aggregate on axes2=" + y)


    def _get_counts(self, axis, query=None, **extra_filters):
        if axis in DATES:
            interval = axis
            axis = 'date'
        else:
            interval = None

        if query is None: query = self.query

        filters = self.filters.copy()
        filters.update(extra_filters)
        return self.es.aggregate_query(query, filters, axis, date_interval=interval)

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
        params = self.request.query_params or self.request.data
        axes = ("axis{i}".format(**locals()) for i in itertools.count(1))
        return [params[x] for x in itertools.takewhile(params.__contains__, axes)]

    @property
    @cached
    def queries(self):
        params = self.request.query_params or self.request.data
        return [keywordsearch.SearchQuery.from_string(q)
                for q in params.getlist("q")]

    def get_queryset(self):
        return AggregateES(self.axes, self.queries)

    def filter_queryset(self, queryset):
        params = self.request.query_params or self.request.data
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
        return ctx

    def post(self, request, *args, **kwargs):
        # allow for POST requests
        return self.list(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not self.queries:
            raise ParseError("You need to provide a non-empty query (q-parameter)")
        return super(AggregateResource, self).get(request, *args, **kwargs)

    class serializer_class(Serializer):
        count = IntegerField()

        def __init__(self, *args, **kwargs):
            Serializer.__init__(self, *args, **kwargs)
            for x in kwargs["context"]["axes"]:
                self.fields[safe_identifier(x)] = CharField()
