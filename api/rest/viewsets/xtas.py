
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.article import ArticleViewSetMixin

from amcat.tools import amcates
import json


class XTasViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, ArticleViewSetMixin, ViewSet):
    model_key = "xta"# HACK to get xtas in url. Sorry!

    def retrieve(self, request, *args, **kargs):
        aid = int(kargs['article'])
        plugin = kargs['pk']

        result = amcates.ES().get(aid, doc_type=plugin)
        
        member = self.request.QUERY_PARAMS.get("member")
        if member:
            result = result[member]
        
        
        return Response({"results" : result})
        

    
    def list(self, request, *args, **kargs):
        aid = int(kargs['article'])
        body = {"filter":{"and" : [
                    {"term":{"_id":aid}},
                    {"has_parent" : {"type" : "article",
                                     "filter" : {"term":{"_id":aid}}
                                     }
                     }]}}
        result = amcates.ES().search(body, doc_type=None, fields=[], size=9999)

        plugins = [h['_type'] for h in result['hits']['hits']]
        
        return Response({'available_parses' : plugins})
