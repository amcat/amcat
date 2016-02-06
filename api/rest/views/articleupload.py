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
import re
import logging

from rest_framework.exceptions import ValidationError
re_uuid = re.compile("[0-F]{8}-[0-F]{4}-[0-F]{4}-[0-F]{4}-[0-F]{12}", re.I)

def is_uuid(val):
    return isinstance(val, str) and re_uuid.match(val)
    

class ArticleListUploadSerializer(serializers.ListSerializer):

    def to_internal_value(self, data):
        # override to change uuid parents into ids
        # there might be a better place to do this?
        if not isinstance(data, list):
            raise ValidationError("Article upload content should be a list of dicts!")
        internal_uuids = {a['uuid']: a for a in data if a.get('uuid')}
        parent_uuids = {a['parent']: a for a in data if is_uuid(a.get('parent'))}

        to_lookup = set(parent_uuids) - set(internal_uuids)
        existing = {str(uuid): id for (uuid, id) in
                    Article.objects.filter(uuid__in = to_lookup).values_list("uuid", "id")}

        result = []
        for a in data:
            parent = a.get('parent')
            if is_uuid(parent):
                if parent in existing: # update with parent=id from database
                    a['parent'] = existing[parent]
                elif parent in internal_uuids: # add child to parent's children list, remove from result
                    del a['parent']
                    internal_uuids[parent].setdefault('children', []).append(a)
                    continue # don't add this to result
                else:
                    logging.warn("Unknown parent: {parent}".format(**locals()))
                    a['parent'] = None
            result.append(a)
        
        return super(ArticleListUploadSerializer, self).to_internal_value(result)
        
        
        
    def create(self, validated_data):
        def _process_children(article_dicts, parent=None):
            for adict in article_dicts:
                children = adict.pop("children")
                if parent is not None:
                    assert 'parent' not in adict
                    adict['parent'] = parent
                article = Article(**adict)
                yield article
                for a in _process_children(children, parent=article):
                    yield a
                    
        articles = list(_process_children(validated_data))
        articleset = self.context["view"].kwargs.get('articleset')
        if articleset: articleset = ArticleSet.objects.get(pk=articleset)
        Article.create_articles(articles, articleset=articleset)
        return articles
        
class ArticleUploadSerializer(AmCATProjectModelSerializer):
    medium = MediumField(ModelChoiceField(queryset=Medium.objects.all()))
    uuid = CharField(required=False)
    
    class Meta:
        model = Article
        read_only_fields = ('id', 'length', 'insertdate', 'insertscript')
        list_serializer_class = ArticleListUploadSerializer

            
    def to_internal_value(self, data):
        if 'children' not in data:
            data['children'] = []
        return super(ArticleUploadSerializer, self).to_internal_value(data)
        
    def to_representation(self, instance):
        return {"id": instance.id}

    def get_fields(self):
        fields = super(ArticleUploadSerializer, self).get_fields()
        fields["children"] = ArticleUploadSerializer(many=True)
        return fields

    def create(self, validated_data):
        raise Exception("ArticleUpload should only be used as a list / bulk upload")


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
