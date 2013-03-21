from amcat.models import Article
from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer

from rest_framework import serializers

class ArticleMetaSerializer(AmCATModelSerializer):
    class Meta:
        model = Article
        fields = ("id", "date", "project", "medium")

class ArticleMetaResource(AmCATResource):
    model = Article
    serializer_class = ArticleMetaSerializer

    @classmethod
    def get_model_name(cls):
        return "ArticleMeta".lower()
