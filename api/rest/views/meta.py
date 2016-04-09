from api.rest.scrollingpaginator import ScrollingPaginator

from rest_framework.generics import ListAPIView

from rest_framework import serializers

        
class MetaSerializer(serializers.BaseSerializer):
    def to_representation(self, obj):
        return obj
        
class ArticleMetaView(ListAPIView):
    base_name = "scrollmeta"
    model_key = "scrollmeta"
    model = None
    serializer_class = MetaSerializer
    pagination_class = ScrollingPaginator

    def get_queryset(self):
        setid = self.kwargs['articleset_id']
        return {u'filter': {'terms': {u'sets': [setid]}}}
