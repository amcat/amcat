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
from rest_framework import status, serializers
from rest_framework.generics import CreateAPIView
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.fields import CharField

from amcat.models import Article, Medium, ArticleSet
from api.rest.serializer import AmCATProjectModelSerializer
from api.rest.viewsets.article import MediumField

class FlatteningListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        result = serializers.ListSerializer.to_representation(self, data)
        return list(itertools.chain(*result))
    

class ArticleUploadSerializer(AmCATProjectModelSerializer):
    medium = MediumField(ModelChoiceField(queryset=Medium.objects.all()))
    uuid = CharField(required=False)
    
    class Meta:
        model = Article
        read_only_fields = ('id', 'length', 'insertdate', 'insertscript')
        list_serializer_class = FlatteningListSerializer

            
    def to_internal_value(self, data):
        if 'children' not in data:
            data['children'] = []
        return super(ArticleUploadSerializer, self).to_internal_value(data)
        
    def to_representation(self, instance):
        return [{"id": a.id} for a in instance]

    def get_fields(self):
        fields = super(ArticleUploadSerializer, self).get_fields()
        fields["children"] = ArticleUploadSerializer(many=True)
        return fields

    def create(self, validated_data):
        def _process(data, parent=None):
            children = data.pop("children")
            if parent is not None:
                assert 'parent' not in data
                data['parent'] = parent
            article = Article(**data)
            yield article
            for child in children:
                for a in _process(child, parent=article):
                    yield a

        articles = list(_process(validated_data))

        articleset = self.context["view"].kwargs.get('articleset')
        if articleset: articleset = ArticleSet.objects.get(pk=articleset)
        Article.create_articles(articles, articleset=articleset)
        return articles


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
