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


FILTER_FIELDS = "start_date","end_date","mediumid","ids","sets"

class LazyES(object):
    def __init__(self, queries=None, filters=None, fields=None, hits=False):
        self.queries = queries
        self.filters = filters or {}
        self.fields = [f for f in (fields or []) if f != "id"]
        self.es = amcates.ES()
        self.hits = hits
        self._count = None

    @property
    def query(self):
        if self.queries:
            return "\n".join("({q.query})".format(**locals()) for q in self.queries)

    def filter(self, key, value):
        self.filters[key] = value

    def __len__(self):
        if not self._count:
            self._count = self.es.count(self.query, filters=self.filters)
        return self._count
        
    def __getslice__(self, i, j):
        kargs = {}
        fields = self.fields
        if self.query and ("lead" in fields or "headline" in fields):
            kargs["highlight"] = True
        elif "lead" in fields:
            kargs["lead"] = True
        fields = [f for f in fields if f != "lead"] 

        result = self.es.query(self.query, filters=self.filters, fields=fields, 
                               size=(j-i), sort=["id"], from_=i, score=False, **kargs)
        if self.hits:
            def add_hits_column(r):
                r.hits = {q.label : 0 for q in self.queries}
                return r
            
            result_dict = {r.id : add_hits_column(r) for r in result}
            f = dict(ids=list(result_dict.keys()))

            for q in self.queries:
                for hit in self.es.query_all(q.query, filters=f, fields=[]):
                    result_dict[hit.id].hits[q.label] = hit.score
        result = list(result)
        return result

class HighlightField(CharField):
    def field_to_native(self, obj, field_name):
        # use highlighting if available, otherwise fall back to raw text
        source = self.source or field_name
        target = {'lead' : 'text', 'headline' : 'headline'}[source]
        result = getattr(obj, "highlight", {}).get(target)
        if result:
            return " ... ".join(result)
        else:
            return getattr(obj, source, None)
                    

class ScoreField(IntegerField):
    def field_to_native(self, obj, field_name):
        source = self.source or field_name
        return obj.hits.get(source, 0)
        
class SearchResource(AmCATResource):

    @property
    @cached
    def columns(self):
        return self.request.QUERY_PARAMS.getlist("col")
        
    @property
    @cached
    def queries(self):
        params = self.request.QUERY_PARAMS
        return [keywordsearch.SearchQuery.from_string(q)
                for q in params.getlist("q")]
        
    
    def get_queryset(self):
        fields = self.get_serializer().get_fields().keys()
        if "text" in self.columns: fields += ["text"]
        if "lead" in self.columns: fields += ["lead"]
        hits = "hits" in self.columns
        
        return LazyES(self.queries, fields=fields, hits=hits)
        
    def filter_queryset(self, queryset):
        params = self.request.QUERY_PARAMS
        for k in FILTER_FIELDS:
            if k in params:
                queryset.filter(k, params.getlist(k))
        return queryset
    
    @classmethod
    def get_model_name(cls):
        return "search"

    def get_filter_fields(cls):
        return cls.filter_class().filters.keys()
    
    class filter_class(filterset.FilterSet):
        sets = filters.NumberFilter()

        def __init__(self, data=None, queryset=None, prefix=None):
            if queryset is None:
                queryset = LazyES()
            filterset.FilterSet.__init__(self, data, queryset, prefix)
            
        class Meta:
            order_by=True

    def get_serializer_context(self):
        ctx = super(SearchResource, self).get_serializer_context()
        ctx["queries"] = self.queries
        ctx["columns"] = self.columns
        return ctx
            
    class serializer_class(Serializer):
        id = IntegerField()
        date = DateField()
        headline = HighlightField()
        mediumid = IntegerField()
        medium = CharField()
        author = CharField()
        addressee = CharField()
        length = IntegerField()
        
        def __init__(self, *args, **kwargs):
            Serializer.__init__(self, *args, **kwargs)
            ctx = kwargs.get("context", {})
            columns = ctx.get("columns", [])
            queries = ctx.get("queries", None)
            
            if "hits" in columns and queries:
                for q in queries:
                    self.fields[q.label] = ScoreField()
            if "text" in columns:
                self.fields['text'] = CharField()
            if "lead" in columns:
                self.fields['lead'] = HighlightField()
        
                
    @classmethod
    def extra_fields(cls, args):
        """Used by datatable.py for dynamic fields. Hack?"""
        queries = [val for (name, val) in args if name == "q"]
        cols = [val for (name, val) in args if name == "col"]

        if 'hits' in cols:
            for q in queries:
                q = keywordsearch.SearchQuery.from_string(q)
                if q.query != "*":
                    yield q.label
        if 'text' in cols:
            yield 'text'
        if 'lead' in cols:
            yield 'lead'

