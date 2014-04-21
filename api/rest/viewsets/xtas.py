
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

class ArticleXTasSerializer(Serializer):

    @property
    def module(self):
        module = self.context['request'].GET.get('module')
        if not module:
            raise Exception("Please specify the NLP/xTas module to use "
                            "with a module= GET parameter")
        elif not module in dir(ANALYSES):
            raise Exception("Unknown module: {module}".format(**locals()))
        return module

    def field_to_native(self, obj, field_name):
        result =  super(ArticleXTasSerializer, self).field_to_native(obj, field_name)
        if field_name == "results":
            # flatting lists of tokens
            result = itertools.chain(*result)
        return result

    def to_native(self, article):
        saf = get_result(article.pk, self.module)
        return list(self.get_xtas_results(article.pk, saf))

class ArticleLemmataSerializer(ArticleXTasSerializer):

    @property
    def filter_pos(self):
        return self.context['request'].GET.get('pos1')

    def output_token(self, token):
        for key, vals in self.context['request'].GET.iterlists():
            if key in token and token[key] not in vals:
                return False
        return True

    def get_xtas_results(self, aid, saf):
        if self.context['request'].GET.get('sources'):
            return self.get_sources(aid, saf)
        else:
            return self.get_tokens(aid, saf)


    def get_tokens(self, aid, saf):
        for token in saf.get('tokens', []):
            token["aid"] = aid
            if self.output_token(token):
                yield token

    def get_sources(self, aid, saf):
        if not 'tokens' in saf and 'sources' in saf:
            return
        tokendict = {t['id'] : t for t in saf['tokens']}
        for sid, source in enumerate(saf['sources']):
            for place, tokens in source.iteritems():
                for tid in tokens:
                    token = tokendict[tid]
                    if self.output_token(token):
                        token["aid"] = aid
                        token["source_id"] = sid
                        token["source_place"] = place
                        yield token


class XTasLemmataViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, DatatablesMixin, ModelViewSet):
    model_key = "token"
    model = Article
    model_serializer_class = ArticleLemmataSerializer

    def filter_queryset(self, queryset):
        queryset = super(XTasLemmataViewSet, self).filter_queryset(queryset)
        # only(.) would be better on serializer, but meh
        queryset = queryset.filter(articlesets_set=self.articleset).only("pk")
        return queryset
