
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.article import ArticleViewSetMixin
from api.rest.mixins import DatatablesMixin

from amcat.models import RuleSet
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

from rest_framework.serializers import Serializer, ListSerializer
from amcat.models import Article, ArticleSet
from rest_framework.viewsets import ModelViewSet
import itertools

class ArticleXTasSerializer(Serializer):

    class Meta:
        class list_serializer_class(ListSerializer):
            def to_representation(self, data):
                # flatten list of lists
                result = ListSerializer.to_representation(self, data)
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
    
    def to_representation(self, article):
        if article is None: return {}
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
        from saf.saf import SAF
        return SAF(saf).resolve(aid=aid)

    def get_transformed(self, aid, saf, rules):
        ruleset = RuleSet.objects.get(label=rules)
        from syntaxrules.soh import SOHServer
        from syntaxrules.syntaxtree import SyntaxTree
        soh = SOHServer("http://localhost:3030/x")
        t = SyntaxTree(soh)
        for sid in {token['sentence'] for token in saf['tokens']}:
            t.load_saf(saf, sid)
            t.apply_ruleset(ruleset.get_ruleset())
            yield sid


class XTasLemmataViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, DatatablesMixin, ModelViewSet):
    model_key = "token"
    model = Article
    queryset = Article.objects.all()
    serializer_class = ArticleLemmataSerializer

    def filter_queryset(self, queryset):
        queryset = super(XTasLemmataViewSet, self).filter_queryset(queryset)
        # only(.) would be better on serializer, but meh
        queryset = queryset.filter(articlesets_set=self.articleset).only("pk")
        return queryset

from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.decorators import api_view
from amcat.tools.amcatxtas import get_adhoc_result
@api_view(http_method_names=("GET",))
def get_adhoc_tokens(request):
    sentence = request.GET.get('sentence')
    module = request.GET.get('module')
    if not (sentence and module):
        raise APIException("Please provide a 'sentence', 'module' and optional 'codebook' parameter")
    saf = get_adhoc_result(module, sentence)
    serializer = ArticleLemmataSerializer()
    data = list(serializer.get_xtas_results(None, saf))

    return Response(data)
