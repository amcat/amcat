from api.rest.scrollingpaginator import ScrollingPaginator

from rest_framework.generics import ListAPIView

from rest_framework import serializers
from amcat.models import Article
        
class MetaSerializer(serializers.BaseSerializer):
    def to_representation(self, obj):
        return obj

def _get_ids(param, to_int=True):
    for id in param:
        for i in id.split(","):
            yield int(i) if to_int else i

    
class ArticleMetaView(ListAPIView):
    base_name = "scrollmeta"
    model_key = "scrollmeta"
    model = None
    serializer_class = MetaSerializer
    pagination_class = ScrollingPaginator

    def get_queryset(self):
        # TODO: should check permission!
        columns = self.request.query_params.get('columns')
        fields = columns.split(",") if columns else ['date', 'medium']
        page_size = int(self.request.query_params.get("page_size", 10))

        if 'articleset_id' in self.kwargs:
            setid = self.kwargs['articleset_id']
            filter = {'sets': [setid]}
        elif 'id' in self.request.query_params:
            ids = list(_get_ids(self.request.query_params.getlist('id')))
            filter = {'id': ids}
        elif 'uuid' in self.request.query_params:
            uuids = list(_get_ids(self.request.query_params.getlist('uuid'), to_int=False))
            ids = list(Article.objects.filter(uuid__in=uuids).values_list("pk", flat=True))
            filter = {'id': ids}
        else:
            raise Exception("Meta API needs either articleset or id paramter")
        
        return {'body': {u'filter': {'terms': filter}},
                'fields': fields, 'size': page_size}


    def get_renderer_context(self):
        context = super(ArticleMetaView, self).get_renderer_context()
        context["text_columns"] = ["text", "headline"]
        return context

