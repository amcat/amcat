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

"""
API Viewsets for dealing with NLP (pre)processing via xtas
"""

from collections import namedtuple
import itertools
import json
import tempfile
import logging

from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.decorators import api_view
from rest_framework.status import HTTP_200_OK
from rest_framework import serializers
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.viewsets import ModelViewSet, ViewSet, GenericViewSet

from amcat.tools.amcatxtas import get_adhoc_result
from amcat.tools.amcates import ES
from amcat.models import Article, ArticleSet

from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.article import ArticleViewSetMixin
from api.rest.mixins import DatatablesMixin

from amcat.tools.amcatxtas import ANALYSES, get_result, get_results, preprocess_set_background, get_preprocessed_results

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


class ArticleLemmataSerializer(serializers.Serializer):

    class Meta:
        class list_serializer_class(serializers.ListSerializer):
            def to_representation(self, data):
                only_cached = self.context['request'].GET.get('only_cached', 'N')
                only_cached = only_cached[0].lower() in ['1', 'y']
                import time; t = time.time() 
                if only_cached:
                    self.child._cache = dict(get_preprocessed_results(data, self.child.module))
                else:
                    self.child._cache = dict(get_results(data, self.child.module))
                logging.debug("Cached xtas results in {t}s".format(t=time.time()-t))
                result = serializers.ListSerializer.to_representation(self, data)
                # flatten list of lists
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
        from saf.saf import SAF
        if article is None: return {}
        saf = self._cache.get(article.pk)
        if saf is None: return {}
        try:
            result = list(SAF(saf).resolve(aid=article.pk))
            return result
        except:
            with tempfile.NamedTemporaryFile(prefix="saf_{article.pk}_".format(**locals()),
                                             suffix=".json", delete=False) as f:
                json.dump(saf, f)
                logging.exception("Error on resolving saf for article {article.pk}, written to {f.name}"
                                  .format(**locals()))
                raise


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
    
    def get_renderer_context(self):
        context = super(XTasLemmataViewSet, self).get_renderer_context()
        context['fast_csv'] = True 
        return context


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

ModuleCount = namedtuple("ModuleCount", ["module", "n"])

class PreprocessViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, DatatablesMixin,
                        ListModelMixin, CreateModelMixin, GenericViewSet):
    model_key = "preproces"
    model = None
    base_name = "preprocess"

    class serializer_class(serializers.Serializer):
        module = serializers.CharField()
        n = serializers.IntegerField()
    
    def filter_queryset(self, queryset):
        return queryset
    
    def get_queryset(self):
        prefix = "article__"
        class Result(list):
            pass

        result = [ModuleCount("Total #articles", self.articleset.get_count())]
        for t, n in ES().get_child_type_counts(sets=self.articleset.id):
            if t.startswith(prefix) and "xtas.tasks.single" not in t:
                t = t[len(prefix):]
                t = t.replace(u"__", u" \u21D2 ")
                result.append(ModuleCount(module=t, n=n))

        return result

    def get_filter_fields(self):
        return []

    
        
    def perform_create(self, serializer):
        module, n = [serializer.data.get(f) for f in ['module', 'n']]
        preprocess_set_background(self.articleset, module, limit=n)
        
