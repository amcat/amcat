from rest_framework import pagination
from amcat.tools import amcates

from rest_framework.response import Response
from django.core.urlresolvers import reverse 
from rest_framework.utils.urls import replace_query_param

class ScrollingPaginator(pagination.BasePagination):
    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        es = amcates.ES()
        self.page_size = request.query_params.get("page_size", 10)
        scroll_id = request.query_params.get("scroll_id")
        if scroll_id:
            res = es.es.scroll(scroll_id, scroll="1m")
        else:
            fields = ["date", "mediumid"]
            res = es.search(queryset, scroll="1m", fields=fields, size=self.page_size)
        self.total = res['hits']['total']
        self.scroll_id = res['_scroll_id']
        self.done = not res['hits']['hits']
        for hit in res['hits']['hits']:
            item = {'id': hit['_id']}
            item.update({k: v[0] for (k,v) in hit['fields'].iteritems()})
            yield item


    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'results': data,
            'total': self.total,
            "per_page": self.page_size,
        })



    def get_next_link(self):
        if not self.done:
            url = self.request.build_absolute_uri()
            return replace_query_param(url, "scroll_id", self.scroll_id)
