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
API Viewsets for dealing with NLP (pre)processing via nlpipe
"""

from __future__ import unicode_literals, print_function, absolute_import

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

from amcat.models import Article, ArticleSet

from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.article import ArticleViewSetMixin
from api.rest.mixins import DatatablesMixin

from nlpipe.pipeline import get_results
from nlpipe.celery import app
from nlpipe import backend

from KafNafParserPy import KafNafParser
from io import BytesIO

def _get_module(request):
    module = request.GET.get('module')
    if not module:
        raise Exception("Please specify the NLP module to use "
                        "with a module= GET parameter")
    from nlpipe import tasks
    return getattr(tasks, module)

class NLPipeLemmataSerializer(serializers.Serializer):

    class Meta:
        class list_serializer_class(serializers.ListSerializer):
            def to_representation(self, aids):
                # nlpipe / elastic has string ids
                aids = (unicode(aid) for aid in aids)
                self.child._cache = get_results(aids, self.child.module)
                result = serializers.ListSerializer.to_representation(self, aids)
                # flatten list of lists
                result = itertools.chain(*result)
                return result

    @property
    def module(self):
        return _get_module(self.context['request'])
    
    def to_representation(self, aid):
        naf = self._cache[aid].text
        naf = KafNafParser(BytesIO(naf.encode("utf-8")))
        tokendict = {token.get_id(): token for token in naf.get_tokens()}

        for term in naf.get_terms():
            tokens = [tokendict[id] for id in term.get_span().get_span_ids()]
            for token in tokens:
                yield {"aid": aid,
                       "token_id": token.get_id(),
                       "offset": token.get_offset(),
                       "sentence": token.get_sent(),
                       "para": token.get_para(),
                       "word": token.get_text(),
                       "term_id": term.get_id(),
                       "lemma": term.get_lemma(),
                       "pos": term.get_pos()}



class NLPipeLemmataViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, DatatablesMixin, ModelViewSet):
    model_key = "token"
    model = Article
    queryset = Article.objects.all()
    serializer_class = NLPipeLemmataSerializer

    def filter_queryset(self, queryset):
        ids = list(self.articleset.get_article_ids_from_elastic())
        only_cached = self.request.GET.get('only_cached', 'N')
        if only_cached[0].lower() in ['1', 'y', 't']:
            module = _get_module(self.request)
            ids = list(backend.get_cached_document_ids(ids, module.doc_type))
        return ids
    
    def get_renderer_context(self):
        context = super(NLPipeLemmataViewSet, self).get_renderer_context()
        context['fast_csv'] = True 
        return context


ModuleCount = namedtuple("ModuleCount", ["module", "n"])

class PreprocessViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, DatatablesMixin,
                        ListModelMixin, GenericViewSet):
    model_key = "preproces"
    model = None
    base_name = "preprocess"

    class serializer_class(serializers.Serializer):
        module = serializers.CharField()
        n = serializers.IntegerField()
    
    def filter_queryset(self, queryset):
        return queryset
    
    def get_queryset(self):
        ids = list(self.articleset.get_article_ids_from_elastic())        
        result = [ModuleCount("Total #articles", len(ids))]
        from nlpipe.document import count_cached
        for module, n in count_cached(ids):
            result.append(ModuleCount(module, n))
        
        return result

    def get_filter_fields(self):
        return []
