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
        columns = self.request.query_params.get('columns')
        fields = columns.split(",") if columns else ['date']
        page_size = int(self.request.query_params.get("page_size", 10))

        setid = self.kwargs['articleset_id']

        return {'body': {u'filter': {'terms': {u'sets': [setid]}}},
                'fields': fields, 'size': page_size}
