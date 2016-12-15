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

import itertools
import logging

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView

from amcat.models import Article
from amcat.tools import amcates


class NLPipeLemmataSerializer(serializers.Serializer):
    class Meta:
        class list_serializer_class(serializers.ListSerializer):
            def to_representation(self, data):
                result = serializers.ListSerializer.to_representation(self, data)
                result = itertools.chain(*result)
                return result

    def to_representation(self, aid):
        fields = ["title", "text"]
        def sort_key(token):
            field, offset, term = token
            return fields.index(field), offset
        tokens = amcates.ES().get_tokens(aid, fields)
        for (field, position, term) in sorted(tokens, key=sort_key):
            yield {"id": aid, "field": field, "position": position, "word": term}


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
        ids = list(amcates.ES().query_ids(filters={"sets" : [setid]}))
        logging.info("Got {} ids".format(len(ids)))
        return ids


    def get_renderer_context(self):
        context = super(TokensView, self).get_renderer_context()
        context['fast_csv'] = True
        return context
