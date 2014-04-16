
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.article import ArticleViewSetMixin
from api.rest.mixins import DatatablesMixin

from amcat.tools.amcatxtas import ANALYSES, get_result
import json


class XTasViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, ArticleViewSetMixin, ViewSet):
    model_key = "xta"# HACK to get xtas in url. Sorry!

    def retrieve(self, request, *args, **kargs):
        aid = int(kargs['article'])
        plugin = kargs['pk']

        result = get_result(aid, plugin)

        return Response({"results" : result})



    def list(self, request, *args, **kargs):
        plugins = ANALYSES.__dict__

        return Response(plugins)

from rest_framework.serializers import Serializer
from amcat.models import Article, ArticleSet
from rest_framework.viewsets import ModelViewSet
import itertools

class ArticleLemmataSerializer(Serializer):

    def field_to_native(self, obj, field_name):
        result =  super(ArticleLemmataSerializer, self).field_to_native(obj, field_name)
        if field_name == "results":
            # flatting lists of tokens
            result = itertools.chain(*result)
        return result

    @property
    def module(self):
        module = self.context['request'].GET.get('module')
        if not module:
            raise Exception("Please specify the NLP/xTas module to use "
                            "with a module= GET parameter")
        elif not module in dir(ANALYSES):
            raise Exception("Unknown module: {module}".format(**locals()))
        return module

    @property
    def filter_pos(self):
        return self.context['request'].GET.get('pos1')


    def output_token(self, token):
        for key, vals in self.context['request'].GET.iterlists():
            if key in token and token[key] not in vals:
                return False
        return True

    def get_article_lemmata(self, pk):
        saf = get_result(pk, self.module)
        for token in saf.get('tokens', []):
            token["aid"] = pk
            if self.output_token(token):
                yield token

    def to_native(self, article):
        result = list(self.get_article_lemmata(article.pk))
        from django.db import connection
        print connection.queries
        connection.queries = []
        return result


class XTasLemmataViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, DatatablesMixin, ModelViewSet):
    model_key = "token"
    model = Article
    model_serializer_class = ArticleLemmataSerializer

    def filter_queryset(self, queryset):
        queryset = super(XTasLemmataViewSet, self).filter_queryset(queryset)
        # only(.) would be better on serializer, but meh
        queryset = queryset.filter(articlesets_set=self.articleset).only("pk")
        return queryset
