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
import itertools

from django.forms import ModelChoiceField
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.fields import CharField

from amcat.models import Article, Medium, ArticleTree, word_len
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewsets.article import MediumField


class ArticleUploadSerializer(AmCATModelSerializer):
    medium = MediumField(ModelChoiceField(queryset=Medium.objects.all()))
    uuid = CharField(required=False)

    def to_representation(self, instance):
        article, children = instance
        article = super(ArticleUploadSerializer, self).to_representation(article)
        article["children"] = map(self.to_representation, children)
        return article

    def get_fields(self):
        fields = super(ArticleUploadSerializer, self).get_fields()
        fields["children"] = ArticleUploadSerializer(many=True)
        return fields

    def create(self, validated_data):
        children = validated_data.pop("children")
        article = Article(**validated_data)

        if article.length is None:
            article.length = word_len(article.text)

        return (article, map(self.create, children))

    class Meta:
        model = Article


class ArticleUploadView(CreateAPIView):
    """
    Special view for efficiently uploading lots of articles. You can provide
    a list of articles, each having an optional property `children`.
    """
    parser_classes = [JSONParser]
    renderer_classes = [BrowsableAPIRenderer, JSONRenderer]
    serializer_class = ArticleUploadSerializer

    def get(self, request):
        return Response("POST-only.")

    def get_serializer(self, **kwargs):
        return super(ArticleUploadView, self).get_serializer(many=True, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        article_trees = self.perform_create(serializer)
        article_ids = itertools.chain.from_iterable(at.get_ids() for at in article_trees)
        headers = self.get_success_headers(serializer.data)
        return Response(list(article_ids), status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        result = serializer.save()
        trees = map(ArticleTree.from_tuples, result)
        Article.save_trees(trees)
        return trees
