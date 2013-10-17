import math

from django.conf.urls import patterns, url
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.fields import DateField, CharField, IntegerField
from rest_framework.serializers import Serializer
from amcat.tools import amcates
from api.rest.resources.amcatresource import AmCATResource

FILTER_FIELDS = "start_date","end_date","mediumid","ids","sets"

class LazyES(object):
    def __init__(self, query=None, filters=None, fields=None):
        self.query = query
        self.filters = filters or {}
        self.fields = [f for f in (fields or []) if f != "id"]
        self.es = amcates.ES()
        
    def filter(self, key, value):
        self.filters[key] = value

    def __getslice__(self, i, j):
        return self.es.query(self.query, filters=self.filters, fields=self.fields, size=(j-i), sort=["id"], offset=i)

    def __len__(self):
        return self.es.query(self.query, filters=self.filters, fields=[], size=0).total
    
class SearchResource(AmCATResource):
    def get_queryset(self):
        params = self.request.QUERY_PARAMS
        q = params.get("q")
        fields = self.get_serializer().get_fields()
        return LazyES(q, fields=fields.keys())
        
    def filter_queryset(self, queryset):
        params = self.request.QUERY_PARAMS
        for k in FILTER_FIELDS:
            if k in params:
                queryset.filter(k, params[k])
        return queryset
    
    @classmethod
    def get_url_pattern(cls):
        """The url pattern for use in the django urls routing table"""
        pattern = r'^search$'
        return url(pattern, cls.as_view(), name="search")


    class serializer_class(Serializer):
        id = IntegerField()
        date = DateField()
        headline = CharField()
        mediumid = IntegerField()
