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
from io import BytesIO
import bz2

from django.core.cache import cache

from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.decorators import api_view
from rest_framework.status import HTTP_200_OK
from rest_framework import serializers
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.viewsets import ModelViewSet, ViewSet, GenericViewSet
from rest_framework.generics import ListAPIView

from nlpipe.pipeline import get_results
from nlpipe.backend import get_cached_document_ids
from nlpipe.celery import app

from KafNafParserPy import KafNafParser

from amcat.models import Article, ArticleSet
from amcat.tools import amcates

from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.article import ArticleViewSetMixin
from api.rest.mixins import DatatablesMixin

# set nlpipe es settings from amcat es settings
from nlpipe.backend import set_esconfig
import settings
set_esconfig(host=settings.ES_HOST, port=settings.ES_PORT)

def _get_tokens(term_vector, pos_inc=0, offset_inc=0):
    for term, info in term_vector.items():
        for token in info['tokens']:
            token['position'] += pos_inc
            token['start_offset'] += offset_inc
            token['end_offset'] += offset_inc
            token['term'] = term
            yield token

def _tokens_from_vectors(vectors, fields, aid):
    pos_inc, offset_inc = 0, 0
    for field in fields:
        if field not in vectors:
            continue
        tokens = _get_tokens(vectors[field]['terms'],
                             pos_inc=pos_inc, offset_inc=offset_inc)
        tokens = sorted(tokens, key = lambda t:t['position'])
        pos_inc = (tokens[-1]['position'] + 1) if tokens else 0
        offset_inc = (tokens[-1]['end_offset'] + 1) if tokens else 0
        for token in tokens:
            token['aid'] = aid
            yield token


def _termvectors(aids):
    fields = ["headline", "text"]
    for doc in amcates.ES().term_vectors(aids, fields):
        aid = int(doc['_id'])
        yield aid, list(_tokens_from_vectors(doc['term_vectors'], fields, aid))

class NLPipeLemmataSerializer(serializers.Serializer):

    class Meta:
        class list_serializer_class(serializers.ListSerializer):
            def to_representation(self, data):
                module = self.context['view'].module
                if module is None:
                    self.child._cache = dict(_termvectors(data))
                else:
                    self.child._cache = {int(aid): naf for (aid, naf) in get_results(data, module).iteritems()}
                result = serializers.ListSerializer.to_representation(self, data)
                # flatten list of lists
                result = itertools.chain(*result)
                return result


    def to_representation(self, aid):
        result = self._cache[aid]
        renderer = self.context['request'].accepted_renderer
        if getattr(renderer, "raw_output", False):
            return [result]

        if isinstance(result, list):
            return result
        else:
            try:
                return list(self.from_naf(aid, result.text))
            except:
                logging.exception("Error on rendering tokens for {aid}".format(**locals()))
                return []

    def from_naf(self, article, naf):
        def _int(x):
            return None if x is None else int(x)

        naf = KafNafParser(BytesIO(naf.encode("utf-8")))

        deps = {dep.get_to(): (dep.get_function(), dep.get_from())
                for dep in naf.get_dependencies()}
        tokendict = {token.get_id(): token for token in naf.get_tokens()}

        for term in naf.get_terms():
            tokens = [tokendict[id] for id in term.get_span().get_span_ids()]
            for token in tokens:
                tid = term.get_id()
                tok = {"aid": article,
                       "token_id": token.get_id(),
                       "offset": _int(token.get_offset()),
                       "sentence": _int(token.get_sent()),
                       "para": _int(token.get_para()),
                       "word": token.get_text(),
                       "term_id": tid,
                       "lemma": term.get_lemma(),
                       "pos": term.get_pos()}
                if tid in deps:
                    rel, parent = deps[tid]
                    tok['parent'] = parent
                    tok['relation'] = rel.split("/")[-1]
                yield tok

def cache_list(key, items, timeout, max_size=1000000):
    """Cache a list of items in multiple chunks

    memcache has max size of 1MB per object
    so, store a (json+bz2) list directly if it is < max_size
    otherwise, split into chunks and store list of keys
    """
    d = bz2.compress(json.dumps(items), 1)
    nchunks = 1 + len(d) // max_size
    logging.info("Saving {key}: {} // {max_size} = {nchunks}".format(len(d), **locals()))
    if nchunks > 1:
        keys = []
        for i in range(nchunks):
            _key = "{key}__batch_{i}".format(**locals())
            subset = d[i*max_size:(i+1)*max_size]
            cache.set(_key, subset, timeout)
            keys.append(_key)
        cache.set(key, keys, timeout)
    else:
        cache.set(key, d, timeout)

def get_cached_list(key, extend_timeout):
    """Retrieve and reconstruct a list from cache, extending the timeout"""
    result = cache.get(key)
    if result is None:
        return result
    cache.set(key, result, extend_timeout)
    if isinstance(result, list):
        pickled_bytes = BytesIO()
        d = bz2.BZ2Decompressor()
        for key in result:
            val = cache.get(key)
            cache.set(key, val, extend_timeout)
            pickled_bytes.write(d.decompress(val))
        pickled_bytes.seek(0)
        return json.load(pickled_bytes)
    else:
        return json.loads(bz2.decompress(result))

class TokensView(ListAPIView):
    model_key = "token"
    model = Article
    queryset = Article.objects.all()
    serializer_class = NLPipeLemmataSerializer

    @property
    def module(self):
        module = self.request.GET.get('module')
        if not module or module == 'elastic':
            return None
        from nlpipe import tasks
        if not hasattr(tasks, module):
            raise ValidationError("Module {module} not known".format(**locals()))

        return getattr(tasks, module)


    def get_queryset(self):
        setid = int(self.kwargs['articleset_id'])
        only_cached = self.request.GET.get('only_cached', 'N')
        only_cached = only_cached[0].lower() in ['1', 'y']

        cache_key = "api-tokens-ids-{setid}-{module}".format(
            setid=setid, module=self.module.doc_type if only_cached else None)


        reset_cache = self.request.GET.get('reset_cache', 'N')
        reset_cache = reset_cache[0].lower() in ['1', 'y']

        ids = None if reset_cache else get_cached_list(cache_key, 60 * 10)
        logging.info("Cache entry for {cache_key}? {}".format(ids is not None, **locals()))
        if ids is None:
            logging.info("Getting ids".format(**locals()))
            ids = list(amcates.ES().query_ids(filters={"sets" : [setid]}))
            logging.info("Got {} ids".format(len(ids)))


            if only_cached and self.module:
                logging.info("Filtering ids")
                ids = [int(aid) for aid in get_cached_document_ids(ids, self.module.doc_type)]
                logging.info("{} ids left".format(len(ids)))

            cache_list(cache_key, ids, 60 * 10)
        return ids


    def get_renderer_context(self):
        context = super(TokensView, self).get_renderer_context()
        context['fast_csv'] = True
        return context
